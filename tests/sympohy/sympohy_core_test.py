from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.sympohy import (
    extract_acceptance_set,
    inspect_running_issue,
    is_candidate_issue,
    merge_gate_allows_merge,
    migrate_task_labels,
    next_retry_action,
    resolve_resume_point,
    transition_labels,
    validate_commit_subject,
)
from scripts.sympohy.config import SympohyConfig
from scripts.sympohy.core import (
    _phase_from_labels,
    parse_final_verifier_block_findings,
    parse_review_json,
)
from scripts.sympohy.runner import _logical_steps, watch
from scripts.sympohy.systemd import _systemd_escape


class FakeProcess:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.wait_called = False

    def wait(self) -> int:
        self.wait_called = True
        return self.returncode


class SympohyCoreTest(unittest.TestCase):
    def test_extracts_latest_complete_ac_dod_from_body_and_comments(self) -> None:
        body = """
## AC
- [ ] old AC

## DoD
- [ ] old DoD
"""
        comments = [
            {
                "body": """
## AC
- [ ] newer AC

## DoD
- [ ] newer DoD
"""
            }
        ]

        result = extract_acceptance_set(body, comments)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.source, "comment 1")
        self.assertEqual(result.acceptance_criteria, ("newer AC",))
        self.assertEqual(result.definition_of_done, ("newer DoD",))

    def test_missing_complete_ac_dod_blocks_refinement(self) -> None:
        result = extract_acceptance_set("## AC\n- [ ] only AC", [])

        self.assertIsNone(result)

    def test_extracts_ac_dod_after_fenced_markdown_templates(self) -> None:
        body = """
## Requirements template

```md
## Acceptance Criteria

## Open Questions
```

## AC

- [ ] real AC

## DoD

- [ ] real DoD
"""

        result = extract_acceptance_set(body, [])

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.acceptance_criteria, ("real AC",))
        self.assertEqual(result.definition_of_done, ("real DoD",))

    def test_migrates_ready_legacy_task_labels_to_pending_triage(self) -> None:
        labels = migrate_task_labels(
            ("bug", "ai:impl-ready", "area:frontend"),
            issue_state="OPEN",
        )

        self.assertEqual(
            labels,
            (
                "area:frontend",
                "bug",
                "sympohy:pending",
                "sympohy:phase:triage",
            ),
        )

    def test_migrates_legacy_workflow_intent_to_supported_phase(self) -> None:
        labels = migrate_task_labels(
            ("priority:high", "ai:review", "takt:running"),
            issue_state="OPEN",
        )

        self.assertEqual(
            labels,
            (
                "priority:high",
                "sympohy:phase:review",
                "sympohy:running",
            ),
        )

    def test_migrates_closed_legacy_task_to_done_merge(self) -> None:
        labels = migrate_task_labels(("ai:done", "release:next"), issue_state="CLOSED")

        self.assertEqual(
            labels,
            (
                "release:next",
                "sympohy:done",
                "sympohy:phase:finalize",
            ),
        )

    def test_preserves_existing_sympohy_state_when_removing_legacy_labels(self) -> None:
        labels = migrate_task_labels(
            (
                "ai:impl-ready",
                "sympohy:running",
                "sympohy:phase:hooks",
                "kind:bug",
            ),
            issue_state="OPEN",
        )

        self.assertEqual(
            labels,
            (
                "kind:bug",
                "sympohy:phase:hooks",
                "sympohy:running",
            ),
        )

    def test_open_issue_without_sympohy_status_is_candidate(self) -> None:
        issue = {"state": "OPEN", "labels": [{"name": "bug"}]}

        self.assertTrue(is_candidate_issue(issue))

    def test_terminal_status_labels_are_not_candidates(self) -> None:
        for status in ("sympohy:blocked", "sympohy:done"):
            with self.subTest(status=status):
                self.assertFalse(
                    is_candidate_issue(
                        {
                            "state": "OPEN",
                            "labels": [
                                {"name": status},
                                {"name": "sympohy:phase:implement"},
                            ],
                        }
                    )
                )

    def test_pending_issue_without_state_is_stale_candidate(self) -> None:
        issue = {
            "number": 82,
            "state": "OPEN",
            "labels": [
                {"name": "sympohy:pending"},
                {"name": "sympohy:phase:triage"},
            ],
        }

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            inspection = inspect_running_issue(
                issue,
                run_log_root=root,
                now=datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc),
                process_alive=lambda _pid: True,
            )

            self.assertTrue(inspection.stale)
            self.assertEqual(inspection.reason, "missing state")
            self.assertTrue(is_candidate_issue(issue, run_log_root=root))

    def test_fresh_running_issue_with_live_pid_is_not_candidate(self) -> None:
        issue = {
            "number": 82,
            "state": "OPEN",
            "labels": [
                {"name": "enhancement"},
                {"name": "sympohy:running"},
                {"name": "sympohy:phase:implement"},
            ],
        }

        now = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_run_state(root, 82, pid=123, heartbeat=now)

            inspection = inspect_running_issue(
                issue,
                run_log_root=root,
                now=now,
                process_alive=lambda pid: pid == 123,
            )

            self.assertEqual(inspection.phase, "implement")
            self.assertFalse(inspection.stale)
            self.assertIsNone(inspection.reason)
            self.assertFalse(
                is_candidate_issue(
                    issue,
                    run_log_root=root,
                    now=now,
                    process_alive=lambda pid: pid == 123,
                )
            )

    def test_running_issue_uses_state_phase_before_label_phase(self) -> None:
        issue = {
            "number": 82,
            "state": "OPEN",
            "labels": [
                {"name": "sympohy:running"},
                {"name": "sympohy:phase:triage"},
            ],
        }

        now = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_run_state(root, 82, pid=123, heartbeat=now, phase="hooks")

            inspection = inspect_running_issue(
                issue,
                run_log_root=root,
                now=now,
                process_alive=lambda pid: pid == 123,
            )

            self.assertEqual(inspection.phase, "hooks")
            self.assertFalse(inspection.stale)

    def test_running_issue_with_wrong_state_identity_is_stale(self) -> None:
        issue = {
            "number": 82,
            "state": "OPEN",
            "labels": [
                {"name": "sympohy:running"},
                {"name": "sympohy:phase:implement"},
            ],
        }

        now = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "issue-82"
            state_dir.mkdir(parents=True)
            (state_dir / "state.json").write_text(
                json.dumps(
                    {
                        "issue": 79,
                        "run_id": "run-79",
                        "phase": "implement",
                        "pid": 123,
                        "heartbeat": now.isoformat(),
                    }
                ),
                encoding="utf-8",
            )

            inspection = inspect_running_issue(
                issue,
                run_log_root=root,
                now=now,
                process_alive=lambda pid: pid == 123,
            )

        self.assertTrue(inspection.stale)
        self.assertEqual(inspection.reason, "invalid state")

    def test_running_issue_without_state_is_stale_candidate(self) -> None:
        issue = {
            "number": 82,
            "state": "OPEN",
            "labels": [
                {"name": "sympohy:running"},
                {"name": "sympohy:phase:implement"},
            ],
        }

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            inspection = inspect_running_issue(
                issue,
                run_log_root=root,
                now=datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc),
                process_alive=lambda _pid: True,
            )

            self.assertTrue(inspection.stale)
            self.assertEqual(inspection.reason, "missing state")
            self.assertTrue(is_candidate_issue(issue, run_log_root=root))

    def test_running_issue_with_missing_or_dead_pid_is_stale(self) -> None:
        issue = {
            "number": 82,
            "state": "OPEN",
            "labels": [
                {"name": "sympohy:running"},
                {"name": "sympohy:phase:hooks"},
            ],
        }
        now = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_run_state(root, 82, heartbeat=now)
            missing_pid = inspect_running_issue(
                issue,
                run_log_root=root,
                now=now,
                process_alive=lambda _pid: True,
            )
            self.assertTrue(missing_pid.stale)
            self.assertEqual(missing_pid.reason, "missing pid")

            self._write_run_state(root, 82, pid=456, heartbeat=now)
            dead_pid = inspect_running_issue(
                issue,
                run_log_root=root,
                now=now,
                process_alive=lambda _pid: False,
            )
            self.assertTrue(dead_pid.stale)
            self.assertEqual(dead_pid.reason, "dead pid")

    def test_running_issue_with_old_heartbeat_is_stale(self) -> None:
        issue = {
            "number": 82,
            "state": "OPEN",
            "labels": [
                {"name": "sympohy:running"},
                {"name": "sympohy:phase:review"},
            ],
        }
        now = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_run_state(root, 82, pid=789, heartbeat=now - timedelta(minutes=31))

            inspection = inspect_running_issue(
                issue,
                run_log_root=root,
                now=now,
                process_alive=lambda pid: pid == 789,
            )

            self.assertTrue(inspection.stale)
            self.assertEqual(inspection.phase, "review")
            self.assertEqual(inspection.reason, "stale heartbeat")

            custom_ttl = inspect_running_issue(
                issue,
                run_log_root=root,
                now=now,
                process_alive=lambda pid: pid == 789,
                stale_status_after_minutes=40,
            )
            self.assertFalse(custom_ttl.stale)

    def test_label_transition_keeps_one_status_and_one_phase(self) -> None:
        labels = transition_labels(
            ["bug", "sympohy:pending", "sympohy:phase:triage"],
            status="sympohy:running",
            phase="implement",
        )

        self.assertEqual(
            labels,
            ("bug", "sympohy:phase:implement", "sympohy:running"),
        )

    def test_label_transition_normalizes_legacy_merge_phase(self) -> None:
        labels = transition_labels(
            ["sympohy:running", "sympohy:phase:merge"],
            status="sympohy:done",
            phase="merge",
        )

        self.assertEqual(
            labels,
            ("sympohy:done", "sympohy:phase:finalize"),
        )

    def test_phase_from_labels_normalizes_legacy_merge_aliases(self) -> None:
        self.assertEqual(
            _phase_from_labels(
                ["sympohy:phase:merge", "sympohy:phase:finalize", "sympohy:pending"]
            ),
            "finalize",
        )

    def test_label_transition_removes_stale_status_and_phase_labels(self) -> None:
        labels = transition_labels(
            [
                "bug",
                "sympohy:pending",
                "sympohy:running",
                "sympohy:phase:triage",
                "sympohy:phase:implement",
            ],
            status="sympohy:blocked",
            phase="fix",
        )

        self.assertEqual(labels, ("bug", "sympohy:blocked", "sympohy:phase:fix"))

    def test_resume_point_resolution_maps_phase_labels_to_resume_categories(self) -> None:
        planning = resolve_resume_point(
            [
                {"name": "sympohy:running"},
                {"name": "sympohy:phase:triage"},
            ]
        )
        self.assertEqual(planning.name, "planning")
        self.assertEqual(planning.phase, "triage")
        self.assertFalse(planning.terminal)

        for phase in ("implement", "hooks"):
            with self.subTest(phase=phase):
                resume_point = resolve_resume_point(
                    [
                        {"name": "sympohy:running"},
                        {"name": f"sympohy:phase:{phase}"},
                    ]
                )
                self.assertEqual(resume_point.name, phase)
                self.assertEqual(resume_point.phase, phase)
                self.assertFalse(resume_point.terminal)

        for phase in ("review", "fix", "finalize"):
            with self.subTest(phase=phase):
                resume_point = resolve_resume_point(
                    [
                        {"name": "sympohy:running"},
                        {"name": f"sympohy:phase:{phase}"},
                    ]
                )
                self.assertEqual(resume_point.name, phase)
                self.assertEqual(resume_point.phase, phase)
                self.assertFalse(resume_point.terminal)

    def test_resume_point_resolution_handles_terminal_status_labels(self) -> None:
        blocked = resolve_resume_point(
            [
                "sympohy:blocked",
                "sympohy:phase:implement",
            ]
        )
        self.assertEqual(blocked.name, "blocked")
        self.assertEqual(blocked.phase, "implement")
        self.assertTrue(blocked.terminal)

        completed = resolve_resume_point(
            [
                "sympohy:done",
                "sympohy:phase:finalize",
            ]
        )
        self.assertEqual(completed.name, "completed")
        self.assertEqual(completed.phase, "finalize")
        self.assertTrue(completed.terminal)

    def test_resume_point_resolution_prefers_state_over_terminal_labels(self) -> None:
        blocked_label = resolve_resume_point(
            [
                "sympohy:blocked",
                "sympohy:phase:implement",
            ],
            state={"status": "running", "phase": "review"},
        )
        self.assertEqual(blocked_label.name, "review")
        self.assertEqual(blocked_label.phase, "review")
        self.assertFalse(blocked_label.terminal)

        done_label = resolve_resume_point(
            [
                "sympohy:done",
                "sympohy:phase:finalize",
            ],
            state={"status": "running", "phase": "implement"},
        )
        self.assertEqual(done_label.name, "implement")
        self.assertEqual(done_label.phase, "implement")
        self.assertFalse(done_label.terminal)

    def test_review_json_blocks_critical_high_and_medium_findings(self) -> None:
        result = parse_review_json(
            json.dumps(
                {
                    "findings": [
                        {"severity": "medium", "summary": "missing test"},
                        {
                            "severity": "high",
                            "summary": "fixed already",
                            "status": "resolved",
                        },
                        {"severity": "low", "summary": "nit"},
                    ]
                }
            )
        )

        self.assertFalse(result.approved)
        self.assertEqual(len(result.blocking_findings), 1)

    def test_review_json_accepts_top_level_findings_list(self) -> None:
        result = parse_review_json(
            json.dumps(
                [
                    {
                        "severity": "high",
                        "summary": "missing resume guard",
                        "status": "open",
                    }
                ]
            )
        )

        self.assertFalse(result.approved)
        self.assertEqual(result.blocking_findings[0].summary, "missing resume guard")

    def test_retry_blocks_after_third_failed_attempt(self) -> None:
        self.assertEqual(next_retry_action(1), "retry")
        self.assertEqual(next_retry_action(2), "retry")
        self.assertEqual(next_retry_action(3), "block")

    def test_merge_gate_requires_final_verifier_checks_and_clean_review(self) -> None:
        clean_review = parse_review_json('{"findings":[]}')

        self.assertTrue(
            merge_gate_allows_merge(
                final_verifier={
                    "acceptance_criteria_satisfied": True,
                    "definition_of_done_satisfied": True,
                    "merge_recommendation": "merge",
                },
                github_checks_status="success",
                review_result=clean_review,
            )
        )
        self.assertFalse(
            merge_gate_allows_merge(
                final_verifier={
                    "acceptance_criteria_satisfied": True,
                    "definition_of_done_satisfied": False,
                    "merge_recommendation": "merge",
                },
                github_checks_status="success",
                review_result=clean_review,
            )
        )

    def test_final_verifier_block_findings_require_actionable_schema(self) -> None:
        findings = parse_final_verifier_block_findings(
            {
                "merge_recommendation": "block",
                "findings": [
                    {
                        "kind": "verification",
                        "summary": "CI was not rerun",
                        "evidence": "No post-fix hook log exists",
                        "suggested_fix": "Run task ci after the verifier fix",
                    }
                ],
            }
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "verification")
        self.assertEqual(findings[0].suggested_fix, "Run task ci after the verifier fix")

    def test_final_verifier_block_findings_reject_empty_missing_or_invalid_schema(
        self,
    ) -> None:
        invalid_payloads = (
            {},
            {"findings": []},
            {"findings": "missing list"},
            {"findings": [{"kind": "verification", "summary": "missing evidence"}]},
            {
                "findings": [
                    {
                        "kind": "unsupported",
                        "summary": "bad kind",
                        "evidence": "bad kind",
                        "suggested_fix": "use a supported kind",
                    }
                ]
            },
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                parse_final_verifier_block_findings(payload)

    def test_commit_subject_matches_repository_format(self) -> None:
        self.assertTrue(
            validate_commit_subject("#74 feat(sympohy): add issue runner")
        )
        self.assertFalse(validate_commit_subject("sympohy: add issue runner"))

    def test_systemd_path_escape_preserves_executable_lookup(self) -> None:
        self.assertEqual(
            _systemd_escape('/opt/tools:/tmp/has"quote:/tmp/has%percent'),
            '/opt/tools:/tmp/has\\"quote:/tmp/has%%percent',
        )

    def test_watch_waits_for_spawned_workers_under_systemd(self) -> None:
        process = FakeProcess()
        config = SympohyConfig(
            max_workers=10,
            base_branch="main",
            worktree_root=Path(".sympohy/worktrees"),
            run_log_root=Path(".sympohy/runs"),
            stale_status_after_minutes=30,
            hooks=("task ci",),
            review_max_rounds=5,
            retry_max_attempts=3,
            final_verifier_fix_max_attempts=2,
        )

        with (
            patch(
                "scripts.sympohy.runner.list_candidate_issues",
                return_value=[{"number": 79, "labels": []}],
            ),
            patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
            patch("scripts.sympohy.runner.subprocess.Popen", return_value=process),
        ):
            result = watch(config)

        self.assertEqual(result, 0)
        self.assertTrue(process.wait_called)
        set_issue_state.assert_not_called()

    def test_logical_steps_accepts_string_and_object_planner_output(self) -> None:
        self.assertEqual(
            _logical_steps({"logical_steps": ["write docs", {"description": "run tests"}]}),
            [{"description": "write docs"}, {"description": "run tests"}],
        )

    def _write_run_state(
        self,
        root: Path,
        issue_number: int,
        *,
        pid: int | None = None,
        heartbeat: datetime | None = None,
        phase: str | None = None,
    ) -> None:
        state_dir = root / f"issue-{issue_number}"
        state_dir.mkdir(parents=True, exist_ok=True)
        payload: dict[str, object] = {
            "issue": issue_number,
            "run_id": f"run-{issue_number}",
            "lock": {"run_id": f"run-{issue_number}"},
        }
        if phase is not None:
            payload["phase"] = phase
        if pid is not None:
            payload["pid"] = pid
        if heartbeat is not None:
            payload["heartbeat"] = heartbeat.isoformat()
        (state_dir / "state.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
