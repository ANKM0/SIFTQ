from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.sympohy import (
    extract_acceptance_set,
    inspect_running_issue,
    is_candidate_issue,
    merge_gate_allows_merge,
    next_retry_action,
    resolve_resume_point,
    transition_labels,
    validate_commit_subject,
)
from scripts.sympohy.core import parse_review_json


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
            self._write_run_state(root, 82, pid=789, heartbeat=now - timedelta(minutes=16))

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
                stale_status_after_minutes=20,
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

        for phase in ("review", "fix", "merge"):
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
                "sympohy:phase:merge",
            ]
        )
        self.assertEqual(completed.name, "completed")
        self.assertEqual(completed.phase, "merge")
        self.assertTrue(completed.terminal)

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

    def test_commit_subject_matches_repository_format(self) -> None:
        self.assertTrue(
            validate_commit_subject("#74 feat(sympohy): add issue runner")
        )
        self.assertFalse(validate_commit_subject("sympohy: add issue runner"))

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
        payload: dict[str, object] = {}
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
