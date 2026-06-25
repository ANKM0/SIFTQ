from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.sympohy.config import CodexModelConfig, SympohyConfig
from scripts.sympohy.github import Issue
from scripts.sympohy.core import (
    AcceptanceSet,
    parse_final_verifier_block_findings,
    parse_review_json,
)
from scripts.sympohy.runner import (
    _IssueRunLock,
    _AmbiguousPullRequestError,
    _PullRequestMetadataError,
    _PullRequestMergeability,
    _RunLockedError,
    _RunStateWriter,
    _UnsafeRecoveryError,
    _attempt_pre_review_mergeability_autofix,
    _check_output_with_heartbeat,
    _commit_all_if_new,
    _codex_exec_args,
    _ensure_draft_pull_request,
    _infer_implementation_recovery,
    _prepare_document_artifacts,
    _pull_request_exists,
    _pull_request_merged,
    _push_branch_and_ensure_draft_pull_request,
    _record_run_interrupted,
    _resolve_resume_point_for_issue,
    _resume_fix_phase,
    _resume_late_phase,
    _review_fix_loop,
    _run_final_verifier_fix_round,
    _run_final_verifier_and_merge,
    _run_stage_gate,
    _run_command_with_heartbeat,
    _run_hooks,
    _run_review_fix_round,
    ensure_worktree,
    resume_issue,
    run_issue,
    watch_forever,
)


class SympohyRunnerTest(unittest.TestCase):
    def test_codex_exec_args_include_role_model_and_reasoning(self) -> None:
        config = SympohyConfig(
            max_workers=1,
            base_branch="main",
            worktree_root=Path(".worktrees"),
            run_log_root=Path(".runs"),
            stale_status_after_minutes=30,
            hooks=("task ci",),
            review_max_rounds=1,
            codex_models={
                "review": CodexModelConfig("gpt-5.5", "xhigh"),
            },
        )

        args = _codex_exec_args("review prompt", config=config, role="review")

        self.assertEqual(
            args,
            [
                "codex",
                "exec",
                "--model",
                "gpt-5.5",
                "-c",
                'model_reasoning_effort="xhigh"',
                "review prompt",
            ],
        )

    def test_run_stage_gate_writes_absolute_workspace_to_input(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            worktree = root / "worktree"
            log_dir = root / "runs" / "issue-101"
            worktree.mkdir()
            log_dir.mkdir(parents=True)
            issue = Issue(
                number=101,
                title="Normalize stage gate workspace",
                body="",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )

            def run_stage_gate(
                args: list[str],
                **_kwargs: object,
            ) -> subprocess.CompletedProcess[str]:
                input_path = Path(args[args.index("--input") + 1])
                payload = json.loads(input_path.read_text(encoding="utf-8"))
                workspace = Path(payload["context"]["workspace"])
                self.assertTrue(workspace.is_absolute())
                self.assertEqual(workspace, worktree.resolve())
                return subprocess.CompletedProcess(
                    args=args,
                    returncode=0,
                    stdout='{"status":"pass","stage":"requirements","issue":101}',
                    stderr="",
                )

            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                with patch(
                    "scripts.sympohy.runner.subprocess.run",
                    side_effect=run_stage_gate,
                ):
                    result = _run_stage_gate(
                        "requirements",
                        config=config,
                        issue=issue,
                        log_dir=log_dir,
                        context={
                            "artifact_decisions": {},
                            "workspace": str(worktree.relative_to(root)),
                        },
                        cwd=worktree,
                    )
            finally:
                os.chdir(original_cwd)

        self.assertEqual(result["status"], "pass")

    def test_prepare_document_artifacts_passes_planning_config(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = SympohyConfig(
                max_workers=1,
                base_branch="main",
                worktree_root=root / "worktrees",
                run_log_root=root / "runs",
                stale_status_after_minutes=30,
                hooks=("task ci",),
                review_max_rounds=1,
                stage_gate_command="task ai:sympohy:stage-gate",
            )
            worktree = root / "worktree"
            log_dir = root / "runs" / "issue-59"
            worktree.mkdir()
            log_dir.mkdir(parents=True)
            state = _RunStateWriter(
                issue_number=59,
                log_dir=log_dir,
                base_branch=config.base_branch,
                worktree=worktree,
            )
            issue = Issue(
                number=59,
                title="Persist matrix UI to SQLite",
                body="",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )

            with (
                patch(
                    "scripts.sympohy.runner._codex_json",
                    return_value={
                        "artifact_decisions": {
                            "requirements": {"mode": "not_needed", "reason": "covered"},
                            "design": {"mode": "not_needed", "reason": "covered"},
                            "wireframes": {"mode": "not_needed", "reason": "covered"},
                            "adr": {"mode": "not_needed", "reason": "covered"},
                        }
                    },
                ) as codex_json,
                patch(
                    "scripts.sympohy.runner._run_stage_gate",
                    return_value={"status": "pass"},
                ) as run_stage_gate,
            ):
                result = _prepare_document_artifacts(
                    config=config,
                    issue_ref="#59",
                    issue=issue,
                    acceptance=AcceptanceSet(
                        acceptance_criteria=("AC",),
                        definition_of_done=("DoD",),
                        source="test",
                    ),
                    worktree=worktree,
                    log_dir=log_dir,
                    state=state,
                )

        self.assertTrue(result)
        codex_json.assert_called_once()
        self.assertIs(codex_json.call_args.kwargs["config"], config)
        self.assertEqual(codex_json.call_args.kwargs["role"], "planning")
        self.assertEqual(run_stage_gate.call_count, 4)

    def test_run_review_fix_round_comments_approved_review(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            root = Path(tmp)
            log_dir = root / "runs" / "issue-82"
            log_dir.mkdir(parents=True)
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch=config.base_branch,
            )
            issue = Issue(
                number=82,
                title="Run review fix round logging",
                body="",
                labels=("sympohy:running", "sympohy:phase:review"),
                comments=(),
            )

            with patch("scripts.sympohy.runner.comment") as comment:
                result = _run_review_fix_round(
                    "#82",
                    issue,
                    config,
                    root,
                    log_dir,
                    state,
                    round_index=1,
                    review=parse_review_json('{"findings": []}'),
                    review_json='{"findings": []}',
                    review_pull_request="99",
                    comment_review=True,
                )

        self.assertEqual(result, 0)
        comment.assert_called_once_with("99", '{"findings": []}', cwd=root)

    def test_review_blocks_on_round_after_configured_fix_rounds(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            root = Path(tmp)
            log_dir = root / "runs" / "issue-82"
            worktree = root / "worktree"
            log_dir.mkdir(parents=True)
            worktree.mkdir()
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch=config.base_branch,
                worktree=worktree,
            )
            issue = Issue(
                number=82,
                title="Review upper bound",
                body="",
                labels=("sympohy:running", "sympohy:phase:review"),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                result = _run_review_fix_round(
                    "#82",
                    issue,
                    config,
                    worktree,
                    log_dir,
                    state,
                    round_index=config.review_max_rounds + 1,
                    review=parse_review_json(
                        '{"findings":[{"severity":"high","summary":"still broken"},{"severity":"medium","summary":"tests still failing"}]}'
                    ),
                    review_json=(
                        '{"findings":[{"severity":"high","summary":"still broken"},{"severity":"medium","summary":"tests still failing"}]}'
                    ),
                    review_pull_request="99",
                    comment_review=False,
                )

            state_payload = json.loads(
                (log_dir / "state.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result, 2)
        set_issue_state.assert_called_once()
        body = comment.call_args.args[1]
        self.assertIn("blocking findings remained", body)
        self.assertIn(
            "- remaining blocking findings: high: still broken; medium: tests still failing",
            body,
        )
        self.assertEqual(state_payload["status"], "blocked")
        self.assertEqual(
            state_payload["last_known_progress"]["remaining blocking findings"],
            "high: still broken; medium: tests still failing",
        )

    def test_review_fix_loop_blocks_conflicted_pull_request_after_single_autofix_attempt(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            cwd = root / "worktree"
            log_dir = root / "runs" / "issue-82"
            cwd.mkdir()
            log_dir.mkdir(parents=True)
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch=config.base_branch,
                worktree=cwd,
            )
            issue = Issue(
                number=82,
                title="Block conflicted PR before finalize review",
                body="",
                labels=("sympohy:running", "sympohy:phase:finalize"),
                comments=(),
            )

            with (
                patch(
                    "scripts.sympohy.runner.subprocess.check_output",
                    return_value=json.dumps(
                        {
                            "number": 91,
                            "baseRefName": "main",
                            "headRefName": "issue-82-sympohy",
                            "mergeStateStatus": "DIRTY",
                            "mergeable": "CONFLICTING",
                        }
                    ),
                ),
                patch(
                    "scripts.sympohy.runner._attempt_pre_review_mergeability_autofix",
                    return_value="unmerged paths remain after automatic conflict fix",
                ),
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
                patch("scripts.sympohy.runner._codex_text") as codex_text,
            ):
                result = _review_fix_loop(
                    "#82",
                    issue,
                    config,
                    cwd,
                    log_dir,
                    state,
                    block_phase="finalize",
                )

            self.assertEqual(result, 2)
            codex_text.assert_not_called()
            set_issue_state.assert_called_once_with(
                "#82",
                current_labels=("sympohy:running", "sympohy:phase:finalize"),
                status="sympohy:blocked",
                phase="finalize",
                cwd=cwd,
            )
            comment.assert_called_once()
            self.assertEqual(comment.call_args.args[0], "#82")
            body = comment.call_args.args[1]
            self.assertIn("- failed command: mergeability gate", body)
            self.assertIn("- pr number: 91", body)
            self.assertIn("- base ref: main", body)
            self.assertIn("- head ref: issue-82-sympohy", body)
            self.assertIn(
                "- conflict summary: GitHub reports mergeStateStatus=DIRTY, mergeable=CONFLICTING.",
                body,
            )
            self.assertIn(
                "- recommended next action: sympohy attempted one pre-review auto-merge/auto-fix pass",
                body,
            )
            state_path = log_dir / "state.json"
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["phase"], "finalize")
            self.assertEqual(payload["status"], "blocked")
            progress = payload["last_known_progress"]
            self.assertEqual(progress["failed_command"], "mergeability gate")
            self.assertEqual(progress["pull_request_number"], "91")

    def test_review_fix_loop_rechecks_mergeability_when_pull_request_number_is_supplied(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            cwd = root / "worktree"
            log_dir = root / "runs" / "issue-82"
            cwd.mkdir()
            log_dir.mkdir(parents=True)
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch=config.base_branch,
                worktree=cwd,
            )
            issue = Issue(
                number=82,
                title="Resume fix with conflicted PR",
                body="",
                labels=("sympohy:running", "sympohy:phase:review"),
                comments=(),
            )

            with (
                patch(
                    "scripts.sympohy.runner._ensure_review_mergeability",
                    return_value=None,
                ) as ensure_mergeability,
                patch("scripts.sympohy.runner._codex_text") as codex_text,
            ):
                result = _review_fix_loop(
                    "#82",
                    issue,
                    config,
                    cwd,
                    log_dir,
                    state,
                    pull_request_number="91",
                )

        self.assertEqual(result, 2)
        ensure_mergeability.assert_called_once()
        codex_text.assert_not_called()

    def test_pre_review_mergeability_autofix_stages_resolution_before_unmerged_check(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            cwd = root / "worktree"
            log_dir = root / "runs" / "issue-82"
            cwd.mkdir()
            log_dir.mkdir(parents=True)
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch=config.base_branch,
                worktree=cwd,
            )
            issue = Issue(
                number=82,
                title="Stage merge resolution before verification",
                body="",
                labels=("sympohy:running", "sympohy:phase:review"),
                comments=(),
            )
            mergeability = _PullRequestMergeability(
                number="91",
                base_ref="main",
                head_ref="issue-82-sympohy",
                merge_state_status="DIRTY",
                mergeable="CONFLICTING",
            )

            with (
                patch("scripts.sympohy.runner._check_call_with_heartbeat"),
                patch("scripts.sympohy.runner._run_command_with_heartbeat", return_value=1),
                patch("scripts.sympohy.runner._codex_text"),
                patch("scripts.sympohy.runner._worktree_status", return_value=""),
                patch("scripts.sympohy.runner._worktree_has_conflict_markers", return_value=False),
                patch("scripts.sympohy.runner._run_hooks", return_value=0),
                patch(
                    "scripts.sympohy.runner._merge_has_unmerged_paths",
                    side_effect=[True, False, False],
                ),
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
            ):
                result = _attempt_pre_review_mergeability_autofix(
                    "#82",
                    issue,
                    config,
                    cwd,
                    log_dir,
                    state,
                    phase="review",
                    pull_request=mergeability,
                    log_path=log_dir / "mergeability-autofix.log",
                )

        self.assertIsNone(result)
        add_calls = [
            call_args.args[0]
            for call_args in check_call.call_args_list
            if call_args.args and call_args.args[0][:2] == ["git", "add"]
        ]
        self.assertEqual(add_calls[0], ["git", "add", "-A"])

    def test_pre_review_mergeability_autofix_blocks_dirty_worktree_before_fetch(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            cwd = root / "worktree"
            log_dir = root / "runs" / "issue-82"
            cwd.mkdir()
            log_dir.mkdir(parents=True)
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch=config.base_branch,
                worktree=cwd,
            )
            issue = Issue(
                number=82,
                title="Block dirty mergeability auto-fix",
                body="",
                labels=("sympohy:running", "sympohy:phase:review"),
                comments=(),
            )
            mergeability = _PullRequestMergeability(
                number="91",
                base_ref="main",
                head_ref="issue-82-sympohy",
                merge_state_status="DIRTY",
                mergeable="CONFLICTING",
            )

            with (
                patch("scripts.sympohy.runner._worktree_status", return_value=" M docs/example.md\n"),
                patch("scripts.sympohy.runner._check_call_with_heartbeat") as check_call_with_heartbeat,
                patch("scripts.sympohy.runner._run_command_with_heartbeat") as run_command,
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
            ):
                result = _attempt_pre_review_mergeability_autofix(
                    "#82",
                    issue,
                    config,
                    cwd,
                    log_dir,
                    state,
                    phase="review",
                    pull_request=mergeability,
                    log_path=log_dir / "mergeability-autofix.log",
                )

        self.assertEqual(
            result,
            "worktree has uncommitted changes before automatic conflict fix: M docs/example.md",
        )
        check_call_with_heartbeat.assert_not_called()
        run_command.assert_not_called()
        check_call.assert_not_called()

    def test_review_fix_without_local_changes_reruns_review(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            root = Path(tmp)
            log_dir = root / "runs" / "issue-82"
            worktree = root / "worktree"
            log_dir.mkdir(parents=True)
            worktree.mkdir()
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch=config.base_branch,
                worktree=worktree,
            )
            issue = Issue(
                number=82,
                title="Review metadata-only fix",
                body="",
                labels=("sympohy:running", "sympohy:phase:review"),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner._codex_text") as codex_text,
                patch(
                    "scripts.sympohy.runner._worktree_has_changes",
                    side_effect=(False, False),
                ),
                patch("scripts.sympohy.runner._commit_all_if_new") as commit_all,
            ):
                result = _run_review_fix_round(
                    "#82",
                    issue,
                    config,
                    worktree,
                    log_dir,
                    state,
                    round_index=2,
                    review=parse_review_json(
                        '{"findings":[{"severity":"medium","summary":"metadata"}]}'
                    ),
                    review_json=(
                        '{"findings":[{"severity":"medium","summary":"metadata"}]}'
                    ),
                    review_pull_request="99",
                    comment_review=False,
                    existing_fix_subjects=set(),
                )
            saved_state = json.loads(
                (log_dir / "state.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result, 1)
        codex_text.assert_called_once()
        commit_all.assert_not_called()
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:review"),
            status="sympohy:running",
            phase="fix",
            cwd=worktree,
        )
        self.assertEqual(saved_state["phase"], "review")
        self.assertEqual(
            saved_state["last_known_progress"]["message"],
            "review fix produced no local changes; rerunning review",
        )

    def test_watch_starts_new_candidate_at_pending_triage(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = {
                "number": 82,
                "state": "OPEN",
                "labels": [{"name": "enhancement"}],
            }

            with (
                patch(
                    "scripts.sympohy.runner.list_candidate_issues",
                    return_value=[issue],
                ),
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.subprocess.Popen") as popen,
            ):
                popen.return_value.wait.return_value = 0

                result = watch_forever(
                    config,
                    poll_interval_seconds=1,
                    stop_after_polls=1,
                    sleep=lambda _seconds: None,
                )

        self.assertEqual(result, 0)
        set_issue_state.assert_not_called()
        command = popen.call_args.args[0]
        self.assertEqual(command[-2:], ["run", "#82"])

    def test_watch_routes_stale_running_candidate_to_resume(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = {
                "number": 82,
                "state": "OPEN",
                "labels": [
                    {"name": "sympohy:running"},
                    {"name": "sympohy:phase:implement"},
                ],
            }

            with (
                patch(
                    "scripts.sympohy.runner.list_candidate_issues",
                    return_value=[issue],
                ),
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.subprocess.Popen") as popen,
            ):
                popen.return_value.wait.return_value = 0

                result = watch_forever(
                    config,
                    poll_interval_seconds=1,
                    stop_after_polls=1,
                    sleep=lambda _seconds: None,
                )

        self.assertEqual(result, 0)
        set_issue_state.assert_not_called()
        command = popen.call_args.args[0]
        self.assertEqual(command[-2:], ["resume", "#82"])

    def test_watch_routes_stale_pending_candidate_to_resume(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = {
                "number": 82,
                "state": "OPEN",
                "labels": [
                    {"name": "sympohy:pending"},
                    {"name": "sympohy:phase:triage"},
                ],
            }

            with (
                patch(
                    "scripts.sympohy.runner.list_candidate_issues",
                    return_value=[issue],
                ),
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.subprocess.Popen") as popen,
            ):
                popen.return_value.wait.return_value = 0

                result = watch_forever(
                    config,
                    poll_interval_seconds=1,
                    stop_after_polls=1,
                    sleep=lambda _seconds: None,
                )

        self.assertEqual(result, 0)
        set_issue_state.assert_not_called()
        command = popen.call_args.args[0]
        self.assertEqual(command[-2:], ["resume", "#82"])

    def test_watch_prioritizes_stale_running_before_new_candidates(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = SympohyConfig(
                max_workers=1,
                base_branch="main",
                worktree_root=root / "worktrees",
                run_log_root=root / "runs",
                stale_status_after_minutes=30,
                hooks=("task ci",),
                review_max_rounds=5,
                retry_max_attempts=3,
                final_verifier_fix_max_attempts=2,
                stage_gate_command=None,
            )
            new_issue = {
                "number": 81,
                "state": "OPEN",
                "labels": [{"name": "enhancement"}],
            }
            stale_running = {
                "number": 82,
                "state": "OPEN",
                "labels": [
                    {"name": "sympohy:running"},
                    {"name": "sympohy:phase:implement"},
                ],
            }

            with (
                patch(
                    "scripts.sympohy.runner.list_candidate_issues",
                    return_value=[new_issue, stale_running],
                ),
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.subprocess.Popen") as popen,
            ):
                popen.return_value.wait.return_value = 0

                result = watch_forever(
                    config,
                    poll_interval_seconds=1,
                    stop_after_polls=1,
                    sleep=lambda _seconds: None,
                )

        self.assertEqual(result, 0)
        set_issue_state.assert_not_called()
        command = popen.call_args.args[0]
        self.assertEqual(command[-2:], ["resume", "#82"])

    def test_watch_refills_available_worker_slots_on_next_poll(self) -> None:
        class FakeProcess:
            def __init__(self) -> None:
                self.wait_called = False
                self.poll_calls = 0

            def poll(self) -> int | None:
                self.poll_calls += 1
                return 0

            def wait(self) -> int:
                self.wait_called = True
                return 0

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = SympohyConfig(
                max_workers=1,
                base_branch="main",
                worktree_root=root / "worktrees",
                run_log_root=root / "runs",
                stale_status_after_minutes=30,
                hooks=("task ci",),
                review_max_rounds=5,
                retry_max_attempts=3,
                final_verifier_fix_max_attempts=2,
                stage_gate_command=None,
            )
            first_issue = {
                "number": 81,
                "state": "OPEN",
                "labels": [{"name": "enhancement"}],
            }
            second_issue = {
                "number": 82,
                "state": "OPEN",
                "labels": [{"name": "documentation"}],
            }
            processes = [FakeProcess(), FakeProcess()]

            with (
                patch(
                    "scripts.sympohy.runner.list_candidate_issues",
                    side_effect=[[first_issue], [second_issue]],
                ),
                patch(
                    "scripts.sympohy.runner.subprocess.Popen",
                    side_effect=processes,
                ) as popen,
            ):
                result = watch_forever(
                    config,
                    poll_interval_seconds=1,
                    stop_after_polls=2,
                    sleep=lambda _seconds: None,
                )

        self.assertEqual(result, 0)
        self.assertEqual(popen.call_args_list[0].args[0][-2:], ["run", "#81"])
        self.assertEqual(popen.call_args_list[1].args[0][-2:], ["run", "#82"])
        self.assertTrue(processes[1].wait_called)

    def test_watch_routes_dead_pid_running_candidate_to_resume(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            state_dir = config.run_log_root / "issue-82"
            state_dir.mkdir(parents=True)
            (state_dir / "state.json").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "phase": "hooks",
                        "status": "running",
                        "pid": 98765,
                        "heartbeat": datetime.now(timezone.utc).isoformat(),
                    }
                ),
                encoding="utf-8",
            )
            issue = {
                "number": 82,
                "state": "OPEN",
                "labels": [
                    {"name": "sympohy:running"},
                    {"name": "sympohy:phase:hooks"},
                ],
            }

            with (
                patch(
                    "scripts.sympohy.runner.list_candidate_issues",
                    return_value=[issue],
                ),
                patch("scripts.sympohy.core._process_alive", return_value=False),
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.subprocess.Popen") as popen,
            ):
                popen.return_value.wait.return_value = 0

                result = watch_forever(
                    config,
                    poll_interval_seconds=1,
                    stop_after_polls=1,
                    sleep=lambda _seconds: None,
                )

        self.assertEqual(result, 0)
        set_issue_state.assert_not_called()
        command = popen.call_args.args[0]
        self.assertEqual(command[-2:], ["resume", "#82"])

    def test_resume_issue_bootstraps_missing_run_state(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Recover stale run",
                body="",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.run_issue", return_value=0) as run_issue,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                result = resume_issue("#82", config)

            state = json.loads(
                (config.run_log_root / "issue-82" / "state.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result, 0)
        run_issue.assert_called_once_with(
            "#82",
            config,
            recover=True,
            from_resume=True,
            resume_point="implement",
        )
        set_issue_state.assert_not_called()
        comment.assert_not_called()
        self.assertEqual(state["phase"], "implement")
        self.assertEqual(state["status"], "running")
        self.assertEqual(
            state["last_known_progress"]["message"],
            "routing stale running issue into resume handling",
        )
        self.assertEqual(state["last_known_progress"]["stale_reason"], "missing state")

    def test_ensure_worktree_reuses_existing_branch_worktree_on_recovery(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            existing_worktree = root / "external-worktree"
            issue = Issue(
                number=82,
                title="Reuse branch worktree",
                body="",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner._branch_exists", return_value=True),
                patch(
                    "scripts.sympohy.runner._worktree_for_branch",
                    return_value=existing_worktree,
                ),
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
            ):
                result = ensure_worktree(issue, config, recover=True)

        self.assertEqual(result, existing_worktree)
        check_call.assert_not_called()

    def test_resume_issue_blocks_invalid_run_state(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Reject mismatched state",
                body="",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )
            state_dir = config.run_log_root / "issue-82"
            state_dir.mkdir(parents=True)
            stale_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=31)
            (state_dir / "state.json").write_text(
                json.dumps(
                    {
                        "issue": 79,
                        "run_id": "wrong-run",
                        "phase": "implement",
                        "status": "running",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
                        "lock": {"run_id": "wrong-run"},
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.run_issue", return_value=0) as run_issue,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                result = resume_issue("#82", config)

            state = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(result, 2)
        run_issue.assert_not_called()
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:implement"),
            status="sympohy:blocked",
            phase="implement",
            cwd=None,
        )
        self.assertIn("invalid run state", comment.call_args.args[1])
        self.assertEqual(state["issue"], 82)
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["phase"], "implement")
        self.assertIn("invalid run state", state["last_known_progress"]["cause"])

    def test_resume_issue_selects_recovery_mode_from_phase_label(self) -> None:
        for phase in ("triage", "implement", "hooks", "review", "fix", "finalize"):
            with self.subTest(phase=phase), TemporaryDirectory() as tmp:
                config = self._config(Path(tmp))
                issue = Issue(
                    number=82,
                    title=f"Recover stale {phase}",
                    body="",
                    labels=("sympohy:running", f"sympohy:phase:{phase}"),
                    comments=(),
                )
                state_dir = config.run_log_root / "issue-82"
                state_dir.mkdir(parents=True)
                stale_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=31)
                (state_dir / "state.json").write_text(
                    json.dumps(
                        {
                            "issue": 82,
                            "run_id": f"stale-{phase}",
                            "phase": phase,
                            "status": "running",
                            "pid": os.getpid(),
                            "heartbeat": stale_heartbeat.isoformat(),
                            "lock": {"run_id": f"stale-{phase}"},
                        }
                    ),
                    encoding="utf-8",
                )

                with (
                    patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                    patch(
                        "scripts.sympohy.runner.run_issue",
                        return_value=0,
                    ) as run_issue,
                ):
                    result = resume_issue("#82", config)

                self.assertEqual(result, 0)
                run_issue.assert_called_once_with(
                    "#82",
                    config,
                    recover=phase != "triage",
                    from_resume=True,
                    resume_point="planning" if phase == "triage" else phase,
                )

    def test_resume_issue_routes_from_state_phase_and_corrects_label(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Recover state-owned phase",
                body="",
                labels=("sympohy:running", "sympohy:phase:triage"),
                comments=(),
            )
            state_dir = config.run_log_root / "issue-82"
            state_dir.mkdir(parents=True)
            stale_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=31)
            (state_dir / "state.json").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "run_id": "stale-hooks",
                        "phase": "hooks",
                        "status": "running",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
                        "lock": {"run_id": "stale-hooks"},
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.run_issue", return_value=0) as run_issue,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
            ):
                result = resume_issue("#82", config)

        self.assertEqual(result, 0)
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:triage"),
            status="sympohy:running",
            phase="hooks",
        )
        run_issue.assert_called_once_with(
            "#82",
            config,
            recover=True,
            from_resume=True,
            resume_point="hooks",
        )

    def test_resume_issue_ignores_active_running_state_for_double_resume_safety(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Already being resumed",
                body="",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )
            state_dir = config.run_log_root / "issue-82"
            state_dir.mkdir(parents=True)
            original_state = {
                "issue": 82,
                "run_id": "active-run",
                "phase": "implement",
                "status": "running",
                "pid": os.getpid(),
                "heartbeat": datetime.now(timezone.utc).isoformat(),
                "lock": {"run_id": "active-run"},
            }
            (state_dir / "state.json").write_text(
                json.dumps(original_state),
                encoding="utf-8",
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.run_issue", return_value=0) as run_issue,
            ):
                result = resume_issue("#82", config)

            state = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        run_issue.assert_not_called()
        self.assertEqual(state, original_state)

    def test_resume_issue_restarts_stale_triage_without_recovery_mode(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Recover stale triage",
                body="",
                labels=("sympohy:running", "sympohy:phase:triage"),
                comments=(),
            )
            state_dir = config.run_log_root / "issue-82"
            state_dir.mkdir(parents=True)
            stale_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=31)
            (state_dir / "state.json").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "run_id": "stale-triage",
                        "phase": "triage",
                        "status": "running",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
                        "lock": {"run_id": "stale-triage"},
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.run_issue", return_value=0) as run_issue,
            ):
                result = resume_issue("#82", config)

        self.assertEqual(result, 0)
        run_issue.assert_called_once_with(
            "#82",
            config,
            recover=False,
            from_resume=True,
            resume_point="planning",
        )

    def test_resumed_planning_run_creates_worktree_without_recovery_mode(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            worktree = root / "worktree"
            worktree.mkdir()
            issue = Issue(
                number=82,
                title="Restart stale triage",
                body="""
## AC
- [ ] restart from planning

## DoD
- [ ] create a fresh issue worktree
""",
                labels=("sympohy:running", "sympohy:phase:triage"),
                comments=(),
            )

            def check_output(args: list[str], **_kwargs: object) -> str:
                if args == ["git", "branch", "--show-current"]:
                    return "issue-82-sympohy\n"
                if args == ["git", "log", "--format=%s", "main..HEAD"]:
                    return ""
                raise AssertionError(f"unexpected check_output: {args}")

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch(
                    "scripts.sympohy.runner.ensure_worktree",
                    return_value=worktree,
                ) as ensure_worktree,
                patch("scripts.sympohy.runner.set_issue_state"),
                patch("scripts.sympohy.runner.comment"),
                patch("scripts.sympohy.runner._issue_branch_exists", return_value=False),
                patch(
                    "scripts.sympohy.runner._codex_json",
                    return_value={"logical_steps": [{"name": "one"}]},
                ),
                patch("scripts.sympohy.runner._codex_text", return_value=""),
                patch("scripts.sympohy.runner._run_hooks", return_value=1),
                patch(
                    "scripts.sympohy.runner._push_branch_and_ensure_draft_pull_request"
                ),
                patch(
                    "scripts.sympohy.runner.subprocess.check_output",
                    side_effect=check_output,
                ),
            ):
                result = run_issue(
                    "#82",
                    config,
                    recover=False,
                    from_resume=True,
                    resume_point="planning",
                )

        self.assertEqual(result, 2)
        ensure_worktree.assert_called_once_with(issue, config, recover=False)

    def test_resumed_planning_run_reuses_existing_branch_without_plan_recovery(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            worktree = root / "worktree"
            worktree.mkdir()
            issue = Issue(
                number=82,
                title="Restart stale pending branch",
                body="""
## AC
- [ ] resume planning after PR creation

## DoD
- [ ] generate the missing implementation plan
""",
                labels=("sympohy:pending", "sympohy:phase:triage"),
                comments=(),
            )

            def check_output(args: list[str], **_kwargs: object) -> str:
                if args == ["git", "branch", "--show-current"]:
                    return "issue-82-sympohy\n"
                if args == ["git", "log", "--format=%s", "main..HEAD"]:
                    return ""
                raise AssertionError(f"unexpected check_output: {args}")

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch(
                    "scripts.sympohy.runner.ensure_worktree",
                    return_value=worktree,
                ) as ensure_worktree,
                patch("scripts.sympohy.runner.set_issue_state"),
                patch("scripts.sympohy.runner.comment"),
                patch("scripts.sympohy.runner._issue_branch_exists", return_value=True),
                patch(
                    "scripts.sympohy.runner._codex_json",
                    return_value={"logical_steps": [{"name": "one"}]},
                ) as codex_json,
                patch("scripts.sympohy.runner._codex_text", return_value=""),
                patch("scripts.sympohy.runner._run_hooks", return_value=1),
                patch(
                    "scripts.sympohy.runner._push_branch_and_ensure_draft_pull_request"
                ),
                patch(
                    "scripts.sympohy.runner.subprocess.check_output",
                    side_effect=check_output,
                ),
            ):
                result = run_issue(
                    "#82",
                    config,
                    recover=False,
                    from_resume=True,
                    resume_point="planning",
                )

        self.assertEqual(result, 2)
        ensure_worktree.assert_called_once_with(issue, config, recover=True)
        codex_json.assert_called_once()

    def test_resume_issue_restarts_stale_pending_without_required_run_state(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Recover stale pending",
                body="",
                labels=("sympohy:pending", "sympohy:phase:triage"),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch(
                    "scripts.sympohy.runner.run_issue",
                    return_value=0,
                ) as run_issue,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                result = resume_issue("#82", config)

        self.assertEqual(result, 0)
        run_issue.assert_called_once_with(
            "#82",
            config,
            recover=False,
            from_resume=False,
            resume_point="planning",
        )
        set_issue_state.assert_not_called()
        comment.assert_not_called()

    def test_resume_issue_restarts_stale_pending_planning_with_existing_branch(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Recover stale pending branch",
                body="",
                labels=("sympohy:pending", "sympohy:phase:triage"),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch(
                    "scripts.sympohy.runner._branch_exists",
                    side_effect=lambda branch: branch == "issue-82-sympohy",
                ),
                patch("scripts.sympohy.runner._remote_branch_exists", return_value=False),
                patch(
                    "scripts.sympohy.runner.run_issue",
                    return_value=0,
                ) as run_issue,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                result = resume_issue("#82", config)

        self.assertEqual(result, 0)
        run_issue.assert_called_once_with(
            "#82",
            config,
            recover=False,
            from_resume=True,
            resume_point="planning",
        )
        set_issue_state.assert_not_called()
        comment.assert_not_called()

    def test_resume_issue_resumes_stale_pending_with_existing_run_state(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Recover stale pending",
                body="",
                labels=("sympohy:pending", "sympohy:phase:triage"),
                comments=(),
            )
            state_dir = config.run_log_root / "issue-82"
            state_dir.mkdir(parents=True)
            stale_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=31)
            (state_dir / "state.json").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "run_id": "stale-pending",
                        "phase": "triage",
                        "status": "running",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
                        "lock": {"run_id": "stale-pending"},
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch(
                    "scripts.sympohy.runner.run_issue",
                    return_value=0,
                ) as run_issue,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
            ):
                result = resume_issue("#82", config)

        self.assertEqual(result, 0)
        set_issue_state.assert_not_called()
        run_issue.assert_called_once_with(
            "#82",
            config,
            recover=False,
            from_resume=True,
            resume_point="planning",
        )

    def test_resume_issue_continues_when_blocked_state_was_unblocked(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Resume unblocked issue",
                body="",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )
            state_dir = config.run_log_root / "issue-82"
            state_dir.mkdir(parents=True)
            stale_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=31)
            (state_dir / "state.json").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "run_id": "blocked-run",
                        "phase": "implement",
                        "status": "blocked",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
                        "lock": {"run_id": "blocked-run"},
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch(
                    "scripts.sympohy.runner.run_issue",
                    return_value=0,
                ) as run_issue,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
            ):
                result = resume_issue("#82", config)

        self.assertEqual(result, 0)
        set_issue_state.assert_not_called()
        run_issue.assert_called_once_with(
            "#82",
            config,
            recover=True,
            from_resume=True,
            resume_point="implement",
        )

    def test_resume_issue_replans_stale_implement_before_plan_exists(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Resume pre-plan interruption",
                body="",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )
            state_dir = config.run_log_root / "issue-82"
            state_dir.mkdir(parents=True)
            stale_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=31)
            (state_dir / "state.json").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "run_id": "pre-plan-run",
                        "phase": "implement",
                        "status": "running",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
                        "lock": {"run_id": "pre-plan-run"},
                        "last_known_progress": {
                            "message": (
                                "pushing initial issue branch and opening draft "
                                "pull request"
                            )
                        },
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch(
                    "scripts.sympohy.runner.run_issue",
                    return_value=0,
                ) as run_issue,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
            ):
                result = resume_issue("#82", config)

        self.assertEqual(result, 0)
        set_issue_state.assert_not_called()
        run_issue.assert_called_once_with(
            "#82",
            config,
            recover=False,
            from_resume=True,
            resume_point="planning",
        )

    def test_resume_issue_keeps_recovery_after_logical_step_progress(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Resume implementation progress",
                body="",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )
            state_dir = config.run_log_root / "issue-82"
            state_dir.mkdir(parents=True)
            stale_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=31)
            (state_dir / "state.json").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "run_id": "logical-step-run",
                        "phase": "implement",
                        "status": "running",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
                        "lock": {"run_id": "logical-step-run"},
                        "last_known_progress": {
                            "message": "implementing logical step",
                            "current_logical_step": 1,
                            "completed_logical_steps": 0,
                            "total_logical_steps": 2,
                        },
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch(
                    "scripts.sympohy.runner.run_issue",
                    return_value=0,
                ) as run_issue,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
            ):
                result = resume_issue("#82", config)

        self.assertEqual(result, 0)
        set_issue_state.assert_not_called()
        run_issue.assert_called_once_with(
            "#82",
            config,
            recover=True,
            from_resume=True,
            resume_point="implement",
        )

    def test_resume_issue_blocks_stale_pending_with_existing_worktree(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            (config.worktree_root / "issue-82").mkdir(parents=True)
            issue = Issue(
                number=82,
                title="Recover stale pending",
                body="""
## AC
- [ ] avoid unsafe pending resume

## DoD
- [ ] existing worktree blocks
""",
                labels=("sympohy:pending", "sympohy:phase:triage"),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.ensure_worktree") as ensure_worktree,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                result = resume_issue("#82", config)

            state = json.loads(
                (config.run_log_root / "issue-82" / "state.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result, 2)
        ensure_worktree.assert_not_called()
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:pending", "sympohy:phase:triage"),
            status="sympohy:blocked",
            phase="triage",
            cwd=None,
        )
        self.assertIn("existing worktree", comment.call_args.args[1])
        self.assertEqual(state["status"], "blocked")
        self.assertIn("existing worktree", state["last_known_progress"]["cause"])

    def test_resume_issue_recovers_stale_pending_with_saved_implementation_state(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Recover stale pending implementation",
                body="",
                labels=("sympohy:pending", "sympohy:phase:triage"),
                comments=(),
            )
            state_dir = config.run_log_root / "issue-82"
            state_dir.mkdir(parents=True)
            stale_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=31)
            (state_dir / "state.json").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "run_id": "stale-pending-implementation",
                        "phase": "implement",
                        "status": "running",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
                        "lock": {"run_id": "stale-pending-implementation"},
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch(
                    "scripts.sympohy.runner.run_issue",
                    return_value=0,
                ) as run_issue,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
            ):
                result = resume_issue("#82", config)

        self.assertEqual(result, 0)
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:pending", "sympohy:phase:triage"),
            status="sympohy:running",
            phase="implement",
        )
        run_issue.assert_called_once_with(
            "#82",
            config,
            recover=True,
            from_resume=True,
            resume_point="implement",
        )

    def test_recovered_run_loads_existing_plan_and_skips_committed_steps(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            worktree = root / "worktree"
            worktree.mkdir()
            log_dir = config.run_log_root / "issue-82"
            log_dir.mkdir(parents=True)
            (log_dir / "plan.json").write_text(
                json.dumps(
                    {
                        "logical_steps": [
                            {"name": "one"},
                            {"name": "two"},
                            {"name": "three"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            issue = Issue(
                number=82,
                title="Recover stale run",
                body="""
## AC
- [ ] recover implementation

## DoD
- [ ] avoid redoing completed steps
""",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )

            status_calls = 0

            def check_output(args: list[str], **_kwargs: object) -> str:
                nonlocal status_calls
                if args == ["git", "log", "--format=%s", "main..HEAD"]:
                    return (
                        "#82 feat(sympohy): implement logical step 2\n"
                        "#82 feat(sympohy): implement logical step 1\n"
                    )
                if args == ["git", "status", "--porcelain"]:
                    status_calls += 1
                    if status_calls == 1:
                        return ""
                    return " M scripts/sympohy/runner.py\n"
                if args == ["git", "rev-list", "--count", "main..HEAD"]:
                    return "2\n"
                if args == ["git", "branch", "--show-current"]:
                    return "issue-82-sympohy\n"
                raise AssertionError(f"unexpected check_output: {args}")

            def codex_json(
                _prompts: list[str],
                *,
                log_path: Path,
                **_kwargs: object,
            ) -> dict[str, object]:
                if log_path.name == "final-verifier-1.json":
                    return {
                        "acceptance_criteria_satisfied": True,
                        "definition_of_done_satisfied": True,
                        "merge_recommendation": "merge",
                    }
                raise AssertionError(
                    "recovery should load the existing implementation plan"
                )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.ensure_worktree", return_value=worktree),
                patch("scripts.sympohy.runner.set_issue_state"),
                patch("scripts.sympohy.runner._run_hooks", return_value=0),
                patch("scripts.sympohy.runner._review_fix_loop", return_value=0),
                patch("scripts.sympohy.runner._codex_json", side_effect=codex_json),
                patch(
                    "scripts.sympohy.runner._codex_text",
                    return_value="",
                ) as codex_text,
                patch(
                    "scripts.sympohy.runner.subprocess.check_output",
                    side_effect=check_output,
                ),
                patch(
                    "scripts.sympohy.runner.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 0),
                ),
                patch(
                    "scripts.sympohy.runner._resolve_pull_request_number",
                    return_value="99",
                ),
                patch("scripts.sympohy.runner.comment"),
                patch("scripts.sympohy.runner._check_call_with_heartbeat"),
                patch("scripts.sympohy.runner.subprocess.check_call"),
            ):
                result = run_issue("#82", config, recover=True)

        self.assertEqual(result, 0)
        codex_text.assert_called_once()
        prompts = codex_text.call_args.args[0]
        self.assertIn("Implement logical step 3", prompts[0])

    def test_resume_issue_continues_clean_worktree_from_next_uncommitted_step(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            worktree = root / "worktree"
            worktree.mkdir()
            log_dir = config.run_log_root / "issue-82"
            log_dir.mkdir(parents=True)
            (log_dir / "plan.json").write_text(
                json.dumps(
                    {
                        "logical_steps": [
                            {"name": "one"},
                            {"name": "two"},
                            {"name": "three"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            stale_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=31)
            (log_dir / "state.json").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "run_id": "stale-implementation",
                        "phase": "implement",
                        "status": "running",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
                        "lock": {"run_id": "stale-implementation"},
                        "worktree": {
                            "path": str(worktree),
                            "branch": "issue-82-sympohy",
                            "base_branch": "main",
                        },
                        "plan_reference": str(log_dir / "plan.json"),
                    }
                ),
                encoding="utf-8",
            )
            issue = Issue(
                number=82,
                title="Recover stale run with partial commits",
                body="""
## AC
- [ ] recover implementation

## DoD
- [ ] avoid redoing completed steps
""",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )

            status_calls = 0

            def check_output(args: list[str], **_kwargs: object) -> str:
                nonlocal status_calls
                if args == ["git", "log", "--format=%s", "main..HEAD"]:
                    return (
                        "#82 feat(sympohy): implement logical step 2\n"
                        "#82 feat(sympohy): implement logical step 1\n"
                    )
                if args == ["git", "status", "--porcelain"]:
                    status_calls += 1
                    if status_calls == 1:
                        return ""
                    return " M scripts/sympohy/runner.py\n"
                if args == ["git", "rev-list", "--count", "main..HEAD"]:
                    return "2\n"
                if args == ["git", "branch", "--show-current"]:
                    return "issue-82-sympohy\n"
                raise AssertionError(f"unexpected check_output: {args}")

            def codex_json(
                _prompts: list[str],
                *,
                log_path: Path,
                **_kwargs: object,
            ) -> dict[str, object]:
                if log_path.name == "final-verifier-1.json":
                    return {
                        "acceptance_criteria_satisfied": True,
                        "definition_of_done_satisfied": True,
                        "merge_recommendation": "merge",
                    }
                raise AssertionError(
                    "resume should load the saved plan instead of re-planning"
                )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.ensure_worktree", return_value=worktree),
                patch("scripts.sympohy.runner.set_issue_state"),
                patch("scripts.sympohy.runner._run_hooks", return_value=0),
                patch("scripts.sympohy.runner._review_fix_loop", return_value=0),
                patch("scripts.sympohy.runner._codex_json", side_effect=codex_json),
                patch(
                    "scripts.sympohy.runner._codex_text",
                    return_value="",
                ) as codex_text,
                patch(
                    "scripts.sympohy.runner.subprocess.check_output",
                    side_effect=check_output,
                ),
                patch(
                    "scripts.sympohy.runner.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 0),
                ),
                patch(
                    "scripts.sympohy.runner._resolve_pull_request_number",
                    return_value="99",
                ),
                patch("scripts.sympohy.runner.comment"),
                patch("scripts.sympohy.runner._check_call_with_heartbeat"),
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
            ):
                result = resume_issue("#82", config)

        self.assertEqual(result, 0)
        codex_text.assert_called_once()
        prompts = codex_text.call_args.args[0]
        self.assertIn("Implement logical step 3", prompts[0])
        self.assertNotIn("Implement logical step 1", prompts[0])
        commands = [call.args[0] for call in check_call.call_args_list]
        self.assertIn(
            [
                "git",
                "commit",
                "-m",
                "#82 feat(sympohy): implement logical step 3",
            ],
            commands,
        )

    def test_implementation_recovery_blocks_dirty_worktree(self) -> None:
        def check_output(args: list[str], **_kwargs: object) -> str:
            if args == ["git", "log", "--format=%s", "main..HEAD"]:
                return "#82 feat(sympohy): implement logical step 1\n"
            if args == ["git", "status", "--porcelain"]:
                return " M scripts/sympohy/runner.py\n"
            raise AssertionError(f"unexpected check_output: {args}")

        with patch(
            "scripts.sympohy.runner.subprocess.check_output",
            side_effect=check_output,
        ):
            recovery = _infer_implementation_recovery(
                82,
                cwd=Path("/tmp/worktree"),
                base_branch="main",
                total_steps=3,
            )

        self.assertEqual(recovery.committed_logical_steps, 1)
        self.assertIsNone(recovery.worktree_logical_step)
        self.assertFalse(recovery.worktree_clean)
        self.assertIsNotNone(recovery.unsafe_reason)
        assert recovery.unsafe_reason is not None
        self.assertIn("worktree has uncommitted changes", recovery.unsafe_reason)
        self.assertIn("scripts/sympohy/runner.py", recovery.unsafe_reason)
        self.assertFalse(recovery.should_reuse_worktree(2))
        self.assertEqual(recovery.resume_action(3), "block_unsafe_resume")

    def test_implementation_recovery_blocks_inconsistent_step_commits(self) -> None:
        def check_output(args: list[str], **_kwargs: object) -> str:
            if args == ["git", "log", "--format=%s", "main..HEAD"]:
                return (
                    "#82 feat(sympohy): implement logical step 3\n"
                    "#82 feat(sympohy): implement logical step 1\n"
                )
            if args == ["git", "status", "--porcelain"]:
                return ""
            raise AssertionError(f"unexpected check_output: {args}")

        with patch(
            "scripts.sympohy.runner.subprocess.check_output",
            side_effect=check_output,
        ):
            recovery = _infer_implementation_recovery(
                82,
                cwd=Path("/tmp/worktree"),
                base_branch="main",
                total_steps=3,
            )

        self.assertEqual(recovery.committed_logical_steps, 1)
        self.assertIsNotNone(recovery.unsafe_reason)
        assert recovery.unsafe_reason is not None
        self.assertIn("logical step commits are inconsistent", recovery.unsafe_reason)
        self.assertIn("[3]", recovery.unsafe_reason)

    def test_implementation_recovery_blocks_when_base_branch_cannot_be_inspected(
        self,
    ) -> None:
        with patch(
            "scripts.sympohy.runner.subprocess.check_output",
            side_effect=subprocess.CalledProcessError(128, ["git", "log"]),
        ):
            recovery = _infer_implementation_recovery(
                82,
                cwd=Path("/tmp/worktree"),
                base_branch="main",
                total_steps=3,
            )

        self.assertEqual(recovery.committed_logical_steps, 0)
        self.assertIsNotNone(recovery.unsafe_reason)
        assert recovery.unsafe_reason is not None
        self.assertIn("could not inspect logical step commits", recovery.unsafe_reason)

    def test_implementation_recovery_blocks_when_worktree_status_cannot_be_inspected(
        self,
    ) -> None:
        def check_output(args: list[str], **_kwargs: object) -> str:
            if args == ["git", "log", "--format=%s", "main..HEAD"]:
                return "#82 feat(sympohy): implement logical step 1\n"
            if args == ["git", "status", "--porcelain"]:
                raise subprocess.CalledProcessError(128, args)
            raise AssertionError(f"unexpected check_output: {args}")

        with patch(
            "scripts.sympohy.runner.subprocess.check_output",
            side_effect=check_output,
        ):
            recovery = _infer_implementation_recovery(
                82,
                cwd=Path("/tmp/worktree"),
                base_branch="main",
                total_steps=3,
            )

        self.assertEqual(recovery.committed_logical_steps, 1)
        self.assertIsNotNone(recovery.unsafe_reason)
        assert recovery.unsafe_reason is not None
        self.assertIn("could not inspect worktree status", recovery.unsafe_reason)

    def test_recovered_run_blocks_when_saved_plan_is_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            worktree = root / "worktree"
            worktree.mkdir()
            issue = Issue(
                number=82,
                title="Recover stale run",
                body="""
## AC
- [ ] recover implementation

## DoD
- [ ] avoid unsafe resume
""",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.ensure_worktree", return_value=worktree),
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
                patch("scripts.sympohy.runner._codex_json") as codex_json,
                patch("scripts.sympohy.runner._codex_text") as codex_text,
                patch(
                    "scripts.sympohy.runner.subprocess.check_output",
                    return_value="issue-82-sympohy\n",
                ),
            ):
                result = run_issue("#82", config, recover=True)

        self.assertEqual(result, 2)
        codex_json.assert_not_called()
        codex_text.assert_not_called()
        set_issue_state.assert_any_call(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:implement"),
            status="sympohy:blocked",
            phase="implement",
            cwd=worktree,
        )
        self.assertIn(
            "missing or invalid saved implementation plan",
            comment.call_args.args[1],
        )

    def test_resume_issue_blocks_dirty_worktree_during_implementation_recovery(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            worktree = root / "worktree"
            worktree.mkdir()
            log_dir = config.run_log_root / "issue-82"
            log_dir.mkdir(parents=True)
            (log_dir / "plan.json").write_text(
                json.dumps(
                    {
                        "logical_steps": [
                            {"name": "one"},
                            {"name": "two"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            stale_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=31)
            (log_dir / "state.json").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "run_id": "stale-dirty-implementation",
                        "phase": "implement",
                        "status": "running",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
                        "lock": {"run_id": "stale-dirty-implementation"},
                        "worktree": {
                            "path": str(worktree),
                            "branch": "issue-82-sympohy",
                            "base_branch": "main",
                        },
                        "plan_reference": str(log_dir / "plan.json"),
                    }
                ),
                encoding="utf-8",
            )
            issue = Issue(
                number=82,
                title="Recover dirty implementation",
                body="""
## AC
- [ ] recover implementation safely

## DoD
- [ ] block dirty worktrees
""",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )

            def check_output(args: list[str], **_kwargs: object) -> str:
                if args == ["git", "branch", "--show-current"]:
                    return "issue-82-sympohy\n"
                if args == ["git", "log", "--format=%s", "main..HEAD"]:
                    return "#82 feat(sympohy): implement logical step 1\n"
                if args == ["git", "status", "--porcelain"]:
                    return " M scripts/sympohy/runner.py\n"
                raise AssertionError(f"unexpected check_output: {args}")

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.ensure_worktree", return_value=worktree),
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
                patch("scripts.sympohy.runner._run_hooks") as run_hooks,
                patch("scripts.sympohy.runner._codex_json") as codex_json,
                patch("scripts.sympohy.runner._codex_text") as codex_text,
                patch(
                    "scripts.sympohy.runner.subprocess.check_output",
                    side_effect=check_output,
                ),
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
            ):
                result = resume_issue("#82", config)

            state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(result, 2)
        codex_json.assert_not_called()
        codex_text.assert_not_called()
        run_hooks.assert_not_called()
        check_call.assert_not_called()
        set_issue_state.assert_any_call(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:implement"),
            status="sympohy:blocked",
            phase="implement",
            cwd=worktree,
        )
        self.assertIn("worktree has uncommitted changes", comment.call_args.args[1])
        self.assertEqual(state["phase"], "implement")
        self.assertEqual(state["status"], "blocked")
        self.assertIn(
            "worktree has uncommitted changes",
            state["last_known_progress"]["cause"],
        )

    def test_implementation_recovery_continues_from_clean_next_step(self) -> None:
        def check_output(args: list[str], **_kwargs: object) -> str:
            if args == ["git", "log", "--format=%s", "main..HEAD"]:
                return "#82 feat(sympohy): implement logical step 1\n"
            if args == ["git", "status", "--porcelain"]:
                return ""
            raise AssertionError(f"unexpected check_output: {args}")

        with patch(
            "scripts.sympohy.runner.subprocess.check_output",
            side_effect=check_output,
        ):
            recovery = _infer_implementation_recovery(
                82,
                cwd=Path("/tmp/worktree"),
                base_branch="main",
                total_steps=3,
            )

        self.assertEqual(recovery.committed_logical_steps, 1)
        self.assertIsNone(recovery.worktree_logical_step)
        self.assertTrue(recovery.worktree_clean)
        self.assertEqual(recovery.next_logical_step(3), 2)
        self.assertEqual(recovery.resume_action(3), "implement_next_step")
        self.assertFalse(recovery.implementation_complete(3))

    def test_implementation_recovery_pushes_pr_when_clean_complete(self) -> None:
        def check_output(args: list[str], **_kwargs: object) -> str:
            if args == ["git", "log", "--format=%s", "main..HEAD"]:
                return (
                    "#82 feat(sympohy): implement logical step 2\n"
                    "#82 feat(sympohy): implement logical step 1\n"
                )
            if args == ["git", "status", "--porcelain"]:
                return ""
            raise AssertionError(f"unexpected check_output: {args}")

        with patch(
            "scripts.sympohy.runner.subprocess.check_output",
            side_effect=check_output,
        ):
            recovery = _infer_implementation_recovery(
                82,
                cwd=Path("/tmp/worktree"),
                base_branch="main",
                total_steps=2,
            )

        self.assertEqual(recovery.committed_logical_steps, 2)
        self.assertIsNone(recovery.worktree_logical_step)
        self.assertTrue(recovery.worktree_clean)
        self.assertIsNone(recovery.next_logical_step(2))
        self.assertEqual(recovery.resume_action(2), "push_pr")
        self.assertTrue(recovery.implementation_complete(2))

    def test_recovered_clean_complete_run_skips_implementation_and_pushes_pr(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            worktree = root / "worktree"
            worktree.mkdir()
            log_dir = config.run_log_root / "issue-82"
            log_dir.mkdir(parents=True)
            (log_dir / "plan.json").write_text(
                json.dumps(
                    {
                        "logical_steps": [
                            {"name": "one"},
                            {"name": "two"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            issue = Issue(
                number=82,
                title="Recover complete implementation",
                body="""
## AC
- [ ] recover implementation

## DoD
- [ ] push completed clean work
""",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )

            def check_output(args: list[str], **_kwargs: object) -> str:
                if args == ["git", "log", "--format=%s", "main..HEAD"]:
                    return (
                        "#82 feat(sympohy): implement logical step 2\n"
                        "#82 feat(sympohy): implement logical step 1\n"
                    )
                if args == ["git", "status", "--porcelain"]:
                    return ""
                if args == ["git", "rev-list", "--count", "main..HEAD"]:
                    return "2\n"
                if args == ["git", "branch", "--show-current"]:
                    return "issue-82-sympohy\n"
                raise AssertionError(f"unexpected check_output: {args}")

            def codex_json(
                _prompts: list[str],
                *,
                log_path: Path,
                **_kwargs: object,
            ) -> dict[str, object]:
                if log_path.name == "final-verifier-1.json":
                    return {
                        "acceptance_criteria_satisfied": True,
                        "definition_of_done_satisfied": True,
                        "merge_recommendation": "merge",
                    }
                raise AssertionError(
                    "recovery should not generate a new plan for a complete run"
                )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.ensure_worktree", return_value=worktree),
                patch("scripts.sympohy.runner.set_issue_state"),
                patch("scripts.sympohy.runner._run_hooks") as run_hooks,
                patch("scripts.sympohy.runner._review_fix_loop", return_value=0),
                patch("scripts.sympohy.runner._codex_json", side_effect=codex_json),
                patch("scripts.sympohy.runner._codex_text") as codex_text,
                patch(
                    "scripts.sympohy.runner.subprocess.check_output",
                    side_effect=check_output,
                ),
                patch(
                    "scripts.sympohy.runner.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 1, stdout=""),
                ),
                patch(
                    "scripts.sympohy.runner._resolve_pull_request_number",
                    return_value="99",
                ),
                patch("scripts.sympohy.runner.comment"),
                patch(
                    "scripts.sympohy.runner._check_call_with_heartbeat"
                ) as check_call_with_heartbeat,
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
            ):
                result = run_issue("#82", config, recover=True)

            state = json.loads(
                (config.run_log_root / "issue-82" / "state.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result, 0)
        run_hooks.assert_not_called()
        codex_text.assert_not_called()
        heartbeat_commands = [
            call.args[0] for call in check_call_with_heartbeat.call_args_list
        ]
        self.assertIn(
            ["git", "push", "-u", "origin", "issue-82-sympohy"],
            heartbeat_commands,
        )
        self.assertTrue(
            any(
                command[:6]
                == [
                    "gh",
                    "pr",
                    "create",
                    "--draft",
                    "--fill",
                    "--body-file",
                ]
                for command in heartbeat_commands
            )
        )
        commands = [call.args[0] for call in check_call.call_args_list]
        self.assertNotIn(["git", "add", "-A"], commands)
        self.assertFalse(any(command[:2] == ["git", "commit"] for command in commands))
        self.assertEqual(state["status"], "done")

    def test_resume_issue_does_not_restart_terminal_issue_states(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Already blocked",
                body="",
                labels=("sympohy:blocked", "sympohy:phase:hooks"),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.run_issue", return_value=0) as run_issue,
            ):
                result = resume_issue("#82", config)

            state = json.loads(
                (config.run_log_root / "issue-82" / "state.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result, 0)
        run_issue.assert_not_called()
        self.assertEqual(state["phase"], "hooks")
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["last_known_progress"]["resume_point"], "blocked")

    def test_resume_issue_does_not_restart_completed_issue_states(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Already completed",
                body="",
                labels=("sympohy:done", "sympohy:phase:finalize"),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.run_issue", return_value=0) as run_issue,
            ):
                result = resume_issue("#82", config)

            state = json.loads(
                (config.run_log_root / "issue-82" / "state.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result, 0)
        run_issue.assert_not_called()
        self.assertEqual(state["phase"], "finalize")
        self.assertEqual(state["status"], "done")
        self.assertEqual(state["last_known_progress"]["resume_point"], "completed")

    def test_resume_issue_closes_open_completed_issue_and_restores_done_finalize_labels(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            log_dir = config.run_log_root / "issue-82"
            log_dir.mkdir(parents=True)
            (log_dir / "state.json").write_text(
                json.dumps({"issue": 82, "phase": "hooks", "status": "blocked"}),
                encoding="utf-8",
            )
            issue = Issue(
                number=82,
                title="Completed but still open",
                body="",
                labels=("sympohy:done", "sympohy:phase:hooks"),
                comments=(),
                state="OPEN",
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.run_issue", return_value=0) as run_issue,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
            ):
                result = resume_issue("#82", config)

            state = json.loads(
                (config.run_log_root / "issue-82" / "state.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result, 0)
        run_issue.assert_not_called()
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:done", "sympohy:phase:hooks"),
            status="sympohy:done",
            phase="finalize",
        )
        check_call.assert_called_once_with(["gh", "issue", "close", "#82"])
        self.assertEqual(state["phase"], "finalize")
        self.assertEqual(state["status"], "done")
        self.assertEqual(state["last_known_progress"]["resume_point"], "completed")

    def test_resume_issue_reconciles_completed_issue_over_stale_blocked_state(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            log_dir = config.run_log_root / "issue-82"
            log_dir.mkdir(parents=True)
            (log_dir / "state.json").write_text(
                json.dumps({"issue": 82, "phase": "hooks", "status": "blocked"}),
                encoding="utf-8",
            )
            issue = Issue(
                number=82,
                title="Completed with stale local blocked state",
                body="",
                labels=("sympohy:running", "sympohy:phase:hooks"),
                comments=(),
                state="CLOSED",
                state_reason="COMPLETED",
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.run_issue", return_value=0) as run_issue,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
            ):
                result = resume_issue("#82", config)

            state = json.loads(
                (config.run_log_root / "issue-82" / "state.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result, 0)
        run_issue.assert_not_called()
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:hooks"),
            status="sympohy:done",
            phase="finalize",
        )
        check_call.assert_not_called()
        self.assertEqual(state["phase"], "finalize")
        self.assertEqual(state["status"], "done")
        self.assertEqual(state["last_known_progress"]["resume_point"], "completed")

    def test_resolve_resume_point_for_issue_requires_completed_state_reason(self) -> None:
        completed = _resolve_resume_point_for_issue(
            [{"name": "sympohy:running"}, {"name": "sympohy:phase:hooks"}],
            {"status": "blocked", "phase": "hooks"},
            issue_state="CLOSED",
            issue_state_reason="COMPLETED",
        )
        not_planned = _resolve_resume_point_for_issue(
            [{"name": "sympohy:running"}, {"name": "sympohy:phase:hooks"}],
            {"status": "blocked", "phase": "hooks"},
            issue_state="CLOSED",
            issue_state_reason="NOT_PLANNED",
        )

        self.assertEqual(completed.name, "completed")
        self.assertTrue(completed.terminal)
        self.assertEqual(not_planned.name, "hooks")
        self.assertFalse(not_planned.terminal)

    def test_resume_issue_restores_done_finalize_labels_for_completed_issue(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Completed with stale finalize labels",
                body="",
                labels=("sympohy:done", "sympohy:phase:hooks"),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.run_issue", return_value=0) as run_issue,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
            ):
                result = resume_issue("#82", config)

            state = json.loads(
                (config.run_log_root / "issue-82" / "state.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result, 0)
        run_issue.assert_not_called()
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:done", "sympohy:phase:hooks"),
            status="sympohy:done",
            phase="finalize",
        )
        self.assertEqual(state["phase"], "finalize")
        self.assertEqual(state["status"], "done")

    def test_direct_run_refuses_existing_run_state(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            log_dir = config.run_log_root / "issue-82"
            log_dir.mkdir(parents=True)
            (log_dir / "state.json").write_text(
                json.dumps({"phase": "implement"}),
                encoding="utf-8",
            )
            issue = Issue(
                number=82,
                title="Existing run",
                body="""
## AC
- [ ] avoid duplicate fresh run

## DoD
- [ ] operator is directed to resume
""",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner.ensure_worktree") as ensure_worktree,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                result = run_issue("#82", config)

            state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(result, 2)
        ensure_worktree.assert_not_called()
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:implement"),
            status="sympohy:blocked",
            phase="implement",
            cwd=None,
        )
        self.assertIn("use resume", comment.call_args.args[1])
        self.assertEqual(state["status"], "blocked")
        self.assertIn("use resume", state["last_known_progress"]["cause"])

    def test_direct_run_refuses_existing_remote_issue_branch(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            log_dir = config.run_log_root / "issue-82"
            issue = Issue(
                number=82,
                title="Existing remote branch",
                body="""
## AC
- [ ] avoid duplicate remote branch

## DoD
- [ ] operator is directed to resume
""",
                labels=(),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner.fetch_issue", return_value=issue),
                patch("scripts.sympohy.runner._branch_exists", return_value=False),
                patch("scripts.sympohy.runner._remote_branch_exists", return_value=True),
                patch("scripts.sympohy.runner.ensure_worktree") as ensure_worktree,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                result = run_issue("#82", config)

            state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(result, 2)
        ensure_worktree.assert_not_called()
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:triage"),
            status="sympohy:blocked",
            phase="triage",
            cwd=None,
        )
        self.assertIn("origin/issue-82-sympohy", comment.call_args.args[1])
        self.assertEqual(state["status"], "blocked")
        self.assertIn("origin/issue-82-sympohy", state["last_known_progress"]["cause"])

    def test_ensure_worktree_recovers_existing_issue_branch(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Recover stale run",
                body="",
                labels=(),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner._branch_exists", return_value=True),
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
            ):
                worktree = ensure_worktree(issue, config, recover=True)

        self.assertEqual(worktree, Path(tmp) / "worktrees" / "issue-82")
        check_call.assert_called_once_with(
            [
                "git",
                "worktree",
                "add",
                str(Path(tmp) / "worktrees" / "issue-82"),
                "issue-82-sympohy",
            ]
        )

    def test_ensure_worktree_blocks_fresh_run_with_existing_branch(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Fresh run with stale branch",
                body="",
                labels=(),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner._branch_exists", return_value=True),
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
                self.assertRaisesRegex(RuntimeError, "existing branch"),
            ):
                ensure_worktree(issue, config)

        check_call.assert_not_called()

    def test_ensure_worktree_recovers_remote_issue_branch(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Recover remote branch",
                body="",
                labels=(),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner._branch_exists", return_value=False),
                patch("scripts.sympohy.runner._remote_branch_exists", return_value=True),
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
            ):
                worktree = ensure_worktree(issue, config, recover=True)

        self.assertEqual(worktree, Path(tmp) / "worktrees" / "issue-82")
        check_call.assert_called_once_with(
            [
                "git",
                "worktree",
                "add",
                "-b",
                "issue-82-sympohy",
                str(Path(tmp) / "worktrees" / "issue-82"),
                "origin/issue-82-sympohy",
            ]
        )

    def test_ensure_worktree_blocks_recovery_without_worktree_or_branch(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            issue = Issue(
                number=82,
                title="Recover missing branch",
                body="",
                labels=(),
                comments=(),
            )

            with (
                patch("scripts.sympohy.runner._branch_exists", return_value=False),
                patch("scripts.sympohy.runner._remote_branch_exists", return_value=False),
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
                self.assertRaisesRegex(RuntimeError, "neither worktree"),
            ):
                ensure_worktree(issue, config, recover=True)

        check_call.assert_not_called()

    def test_ensure_worktree_blocks_recovery_from_wrong_branch(self) -> None:
        with TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            worktree = config.worktree_root / "issue-82"
            worktree.mkdir(parents=True)
            issue = Issue(
                number=82,
                title="Recover wrong worktree",
                body="",
                labels=("sympohy:running", "sympohy:phase:implement"),
                comments=(),
            )

            with patch("scripts.sympohy.runner._current_branch", return_value="main"):
                with self.assertRaisesRegex(
                    _UnsafeRecoveryError,
                    "expected issue-82-sympohy",
                ):
                    ensure_worktree(issue, config, recover=True)

    def test_commit_all_if_new_skips_existing_subject(self) -> None:
        with (
            patch("scripts.sympohy.runner._commit_subject_exists", return_value=True),
            patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
        ):
            committed = _commit_all_if_new(
                "#82 feat(sympohy): implement logical step 9",
                cwd=Path("/tmp/worktree"),
                base_branch="main",
            )

        self.assertFalse(committed)
        check_call.assert_not_called()

    def test_commit_all_if_new_allows_empty_logical_step_marker(self) -> None:
        subject = "#82 feat(sympohy): implement logical step 12"
        with (
            patch("scripts.sympohy.runner._commit_subject_exists", return_value=False),
            patch("scripts.sympohy.runner._worktree_has_changes", return_value=False),
            patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
        ):
            committed = _commit_all_if_new(
                subject,
                cwd=Path("/tmp/worktree"),
                base_branch="main",
                allow_empty=True,
            )

        self.assertTrue(committed)
        self.assertEqual(
            [call.args[0] for call in check_call.call_args_list],
            [
                ["git", "add", "-A"],
                ["git", "commit", "--allow-empty", "-m", subject],
            ],
        )

    def test_run_hooks_uses_distinct_log_paths_per_hook(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cwd = root / "worktree"
            log_dir = root / "runs" / "issue-82"
            cwd.mkdir()
            log_dir.mkdir(parents=True)

            with patch(
                "scripts.sympohy.runner._run_command_with_heartbeat",
                return_value=0,
            ) as run_command:
                result = _run_hooks(
                    ("echo first", "echo second"),
                    retry_max_attempts=1,
                    cwd=cwd,
                    log_dir=log_dir,
                )

            self.assertEqual(result, 0)
            self.assertTrue((log_dir / "hook-1-1.log").exists())
            self.assertTrue((log_dir / "hook-2-1.log").exists())
            stdout_names = [
                Path(call.kwargs["stdout"].name).name
                for call in run_command.call_args_list
            ]
            self.assertEqual(stdout_names, ["hook-1-1.log", "hook-2-1.log"])

    def test_check_output_with_heartbeat_streams_stdout_to_log(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_path = root / "codex.log"

            output = _check_output_with_heartbeat(
                [
                    sys.executable,
                    "-c",
                    "import sys; print('first'); sys.stdout.flush(); print('second')",
                ],
                cwd=root,
                log_path=log_path,
            )
            logged_output = log_path.read_text(encoding="utf-8")

        self.assertEqual(output, "first\nsecond\n")
        self.assertEqual(logged_output, output)

    def test_check_output_with_heartbeat_refreshes_during_chatty_stdout(self) -> None:
        heartbeats: list[object] = []
        with TemporaryDirectory() as tmp:
            root = Path(tmp)

            with patch("scripts.sympohy.runner.HEARTBEAT_INTERVAL_SECONDS", 0.05):
                _check_output_with_heartbeat(
                    [
                        sys.executable,
                        "-c",
                        (
                            "import sys, time\n"
                            "for index in range(20):\n"
                            "    print(index)\n"
                            "    sys.stdout.flush()\n"
                            "    time.sleep(0.01)\n"
                        ),
                    ],
                    cwd=root,
                    heartbeat=lambda: heartbeats.append(object()),
                )

        self.assertGreaterEqual(len(heartbeats), 2)

    def test_ensure_draft_pull_request_skips_existing_pr_with_non_empty_body(self) -> None:
        with (
            patch(
                "scripts.sympohy.runner._current_branch",
                return_value="issue-82-sympohy",
            ),
            patch("scripts.sympohy.runner._pull_request_exists", return_value=True),
            patch(
                "scripts.sympohy.runner.subprocess.check_output",
                return_value=json.dumps(
                    {
                        "number": 91,
                        "body": (
                            "## Issue Traceability\n- Closes #82\n\n"
                            "## 概要\nsummary\n\n"
                            "## 動作確認結果\nvalidation\n"
                        ),
                    }
                ),
            ) as check_output,
            patch(
                "scripts.sympohy.runner._check_call_with_heartbeat"
            ) as check_call_with_heartbeat,
        ):
            _ensure_draft_pull_request(cwd=Path("/tmp/worktree"))

        check_output.assert_called_once_with(
            ["gh", "pr", "view", "--json", "number,body"],
            cwd=Path("/tmp/worktree"),
            text=True,
        )
        check_call_with_heartbeat.assert_not_called()

    def test_ensure_draft_pull_request_backfills_empty_existing_pr_body(self) -> None:
        captured: dict[str, object] = {}

        def check_call_with_heartbeat(command: list[str], **_kwargs: object) -> None:
            captured["command"] = command
            body_file = Path(command[command.index("--body-file") + 1])
            captured["body"] = body_file.read_text(encoding="utf-8")

        with TemporaryDirectory() as tmp:
            worktree = Path(tmp)
            with (
                patch(
                    "scripts.sympohy.runner._current_branch",
                    return_value="issue-82-sympohy",
                ),
                patch("scripts.sympohy.runner._pull_request_exists", return_value=True),
                patch(
                    "scripts.sympohy.runner.subprocess.check_output",
                    return_value=json.dumps({"number": 91, "body": " \n"}),
                ),
                patch(
                    "scripts.sympohy.runner._check_call_with_heartbeat",
                    side_effect=check_call_with_heartbeat,
                ),
            ):
                _ensure_draft_pull_request(cwd=worktree)

        self.assertEqual(captured["command"][:4], ["gh", "pr", "edit", "91"])
        self.assertIn("## Issue Traceability", str(captured["body"]))
        self.assertIn("- Closes #82", str(captured["body"]))
        self.assertIn("## 概要", str(captured["body"]))
        self.assertIn("## 動作確認結果", str(captured["body"]))

    def test_ensure_draft_pull_request_backfills_existing_pr_missing_required_metadata(self) -> None:
        captured: dict[str, object] = {}

        def check_call_with_heartbeat(command: list[str], **_kwargs: object) -> None:
            captured["command"] = command
            body_file = Path(command[command.index("--body-file") + 1])
            captured["body"] = body_file.read_text(encoding="utf-8")

        with TemporaryDirectory() as tmp:
            worktree = Path(tmp)
            with (
                patch(
                    "scripts.sympohy.runner._current_branch",
                    return_value="issue-82-sympohy",
                ),
                patch("scripts.sympohy.runner._pull_request_exists", return_value=True),
                patch(
                    "scripts.sympohy.runner.subprocess.check_output",
                    return_value=json.dumps({"number": 91, "body": "## Issue Traceability\n- Closes #82\n"}),
                ),
                patch(
                    "scripts.sympohy.runner._check_call_with_heartbeat",
                    side_effect=check_call_with_heartbeat,
                ),
            ):
                _ensure_draft_pull_request(cwd=worktree)

        self.assertEqual(captured["command"][:4], ["gh", "pr", "edit", "91"])
        self.assertIn("## Issue Traceability", str(captured["body"]))
        self.assertIn("## 概要", str(captured["body"]))
        self.assertIn("## 動作確認結果", str(captured["body"]))

    def test_ensure_draft_pull_request_blocks_invalid_existing_pr_metadata(self) -> None:
        with (
            patch(
                "scripts.sympohy.runner._current_branch",
                return_value="issue-82-sympohy",
            ),
            patch("scripts.sympohy.runner._pull_request_exists", return_value=True),
            patch(
                "scripts.sympohy.runner.subprocess.check_output",
                return_value="[]",
            ),
        ):
            with self.assertRaises(_PullRequestMetadataError) as context:
                _ensure_draft_pull_request(cwd=Path("/tmp/worktree"))

        self.assertIn(
            "could not inspect existing pull request metadata",
            str(context.exception),
        )

    def test_ensure_draft_pull_request_creates_body_with_traceability_and_template(self) -> None:
        with TemporaryDirectory() as tmp:
            worktree = Path(tmp)
            template_dir = worktree / ".github"
            template_dir.mkdir()
            (template_dir / "pull_request_template.md").write_text(
                "## 概要\n\n## 動作確認結果\n",
                encoding="utf-8",
            )
            captured: dict[str, object] = {}

            def check_call_with_heartbeat(
                command: list[str],
                **_kwargs: object,
            ) -> None:
                captured["command"] = command
                body_file = Path(command[command.index("--body-file") + 1])
                captured["body"] = body_file.read_text(encoding="utf-8")

            with (
                patch(
                    "scripts.sympohy.runner._current_branch",
                    return_value="issue-82-sympohy",
                ),
                patch("scripts.sympohy.runner._pull_request_exists", return_value=False),
                patch(
                    "scripts.sympohy.runner._check_call_with_heartbeat",
                    side_effect=check_call_with_heartbeat,
                ),
            ):
                _ensure_draft_pull_request(cwd=worktree, issue_number=82)

        self.assertEqual(
            list(captured["command"][:6]),
            [
                "gh",
                "pr",
                "create",
                "--draft",
                "--fill",
                "--body-file",
            ],
        )
        self.assertIn("## Issue Traceability", str(captured["body"]))
        self.assertIn("- Closes #82", str(captured["body"]))
        self.assertIn("## 概要", str(captured["body"]))
        self.assertIn("## 動作確認結果", str(captured["body"]))

    def test_ensure_draft_pull_request_uses_fill_and_template(self) -> None:
        captured: dict[str, object] = {}

        def check_call_with_heartbeat(command: list[str], **_kwargs: object) -> None:
            captured["command"] = command
            body_file = Path(command[command.index("--body-file") + 1])
            captured["body"] = body_file.read_text(encoding="utf-8")

        with TemporaryDirectory() as tmp:
            worktree = Path(tmp)
            template_dir = worktree / ".github"
            template_dir.mkdir()
            (template_dir / "pull_request_template.md").write_text(
                "## 概要\n\n## 動作確認結果\n",
                encoding="utf-8",
            )
            with (
                patch(
                    "scripts.sympohy.runner._current_branch",
                    return_value="issue-114-sympohy",
                ),
                patch("scripts.sympohy.runner._pull_request_exists", return_value=False),
                patch(
                    "scripts.sympohy.runner._check_call_with_heartbeat",
                    side_effect=check_call_with_heartbeat,
                ),
            ):
                _ensure_draft_pull_request(cwd=worktree, issue_number=114)

        self.assertEqual(
            captured["command"][:6],
            [
                "gh",
                "pr",
                "create",
                "--draft",
                "--fill",
                "--body-file",
            ],
        )
        self.assertIn("## Issue Traceability", str(captured["body"]))
        self.assertIn("- Closes #114", str(captured["body"]))
        self.assertIn("## 概要", str(captured["body"]))
        self.assertIn("## 動作確認結果", str(captured["body"]))

    def test_push_branch_creates_initial_empty_commit_before_draft_pr(self) -> None:
        events: list[str] = []

        def check_call(command: list[str], **_kwargs: object) -> None:
            events.append(" ".join(command))

        def check_call_with_heartbeat(
            command: list[str],
            **_kwargs: object,
        ) -> None:
            events.append(" ".join(command))

        with (
            patch("scripts.sympohy.runner._branch_has_commits", return_value=False),
            patch(
                "scripts.sympohy.runner.subprocess.check_call",
                side_effect=check_call,
            ),
            patch(
                "scripts.sympohy.runner._check_call_with_heartbeat",
                side_effect=check_call_with_heartbeat,
            ),
            patch("scripts.sympohy.runner._ensure_draft_pull_request") as ensure_draft_pull_request,
        ):
            _push_branch_and_ensure_draft_pull_request(
                cwd=Path("/tmp/worktree"),
                branch="issue-82-sympohy",
                issue_number=82,
                base_branch="main",
            )

        self.assertEqual(
            events,
            [
                "git commit --allow-empty -m #82 chore(sympohy): open draft pull request",
                "git push -u origin issue-82-sympohy",
            ],
        )
        ensure_draft_pull_request.assert_called_once_with(
            cwd=Path("/tmp/worktree"),
            issue_number=82,
            heartbeat=None,
        )

    def test_run_state_writer_persists_required_metadata(self) -> None:
        now = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_dir = root / "runs" / "issue-82"
            worktree = root / "worktrees" / "issue-82"
            plan_path = log_dir / "plan.json"
            writer = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
                worktree=worktree,
                branch="issue-82-sympohy",
                plan_path=plan_path,
                clock=lambda: now,
            )

            writer.write(
                phase="implement",
                progress={
                    "message": "implementing logical step",
                    "current_logical_step": 3,
                    "completed_logical_steps": 2,
                    "total_logical_steps": 5,
                },
            )

            state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(state["issue"], 82)
        self.assertIsInstance(state["run_id"], str)
        self.assertTrue(state["run_id"])
        self.assertEqual(state["phase"], "implement")
        self.assertEqual(state["status"], "running")
        self.assertEqual(state["pid"], os.getpid())
        self.assertEqual(state["heartbeat"], "2026-06-15T12:00:00Z")
        self.assertEqual(state["lock"]["path"], str(log_dir / "run.lock"))
        self.assertEqual(state["lock"]["run_id"], state["run_id"])
        self.assertEqual(state["branch"], "issue-82-sympohy")
        self.assertEqual(state["worktree"]["path"], str(worktree))
        self.assertEqual(state["worktree"]["branch"], "issue-82-sympohy")
        self.assertEqual(state["worktree"]["base_branch"], "main")
        self.assertEqual(state["plan_reference"], str(plan_path))
        self.assertEqual(
            state["last_known_progress"],
            {
                "message": "implementing logical step",
                "current_logical_step": 3,
                "completed_logical_steps": 2,
                "total_logical_steps": 5,
            },
        )
        self.assertIsNone(state["last_recovery"])

    def test_run_state_writer_records_interrupted_state(self) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-82"
            writer = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
            )
            writer.write(
                phase="implement",
                progress={
                    "message": "implementing logical step",
                    "current_logical_step": 5,
                    "completed_logical_steps": 4,
                    "total_logical_steps": 6,
                },
            )

            _record_run_interrupted(writer, signal.SIGTERM)
            state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(state["status"], "interrupted")
        self.assertEqual(state["phase"], "implement")
        self.assertEqual(state["last_known_progress"]["current_logical_step"], 5)
        self.assertEqual(state["last_known_progress"]["message"], "interrupted by signal")
        self.assertEqual(state["last_known_progress"]["signal"], "SIGTERM")
        self.assertEqual(
            state["last_known_progress"]["resume_action"],
            "resume_interrupted_run",
        )

    def test_run_state_writer_records_recovery_log(self) -> None:
        now = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)

        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-82"
            writer = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
                run_id="run-82",
                clock=lambda: now,
            )
            writer.write(phase="implement", progress={"message": "resume"})
            writer.record_recovery(
                "implementation_recovery_inspected",
                {"completed_logical_steps": 2},
            )

            state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))
            recovery_lines = (log_dir / "recovery.log").read_text(
                encoding="utf-8"
            ).splitlines()

        self.assertEqual(state["last_recovery"]["event"], "implementation_recovery_inspected")
        self.assertEqual(state["last_recovery"]["completed_logical_steps"], 2)
        self.assertEqual(len(recovery_lines), 1)
        self.assertEqual(
            json.loads(recovery_lines[0])["event"],
            "implementation_recovery_inspected",
        )

    def test_run_state_writer_refuses_write_after_lock_takeover(self) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-82"
            old_lock = _IssueRunLock(
                issue_number=82,
                log_dir=log_dir,
                run_id="old-run",
                stale_status_after_minutes=30,
            )
            old_lock.acquire()
            old_writer = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                run_id="old-run",
                lock_path=old_lock.path,
                refresh_lock=True,
            )
            old_writer.write(phase="implement", progress={"message": "old"})
            stale = datetime.now(timezone.utc) - timedelta(minutes=31)
            lock_payload = json.loads((log_dir / "run.lock").read_text(encoding="utf-8"))
            lock_payload["heartbeat"] = stale.isoformat()
            (log_dir / "run.lock").write_text(
                json.dumps(lock_payload),
                encoding="utf-8",
            )
            state_payload = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))
            state_payload["heartbeat"] = stale.isoformat()
            (log_dir / "state.json").write_text(
                json.dumps(state_payload),
                encoding="utf-8",
            )

            new_lock = _IssueRunLock(
                issue_number=82,
                log_dir=log_dir,
                run_id="new-run",
                stale_status_after_minutes=30,
            )
            new_lock.acquire()
            new_writer = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                run_id="new-run",
                lock_path=new_lock.path,
                refresh_lock=True,
            )
            new_writer.write(phase="review", progress={"message": "new"})

            with self.assertRaises(_RunLockedError):
                old_writer.write(phase="hooks", progress={"message": "old woke up"})

            state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(state["run_id"], "new-run")
        self.assertEqual(state["last_known_progress"]["message"], "new")

    def test_check_output_terminates_child_when_heartbeat_loses_lock(self) -> None:
        class FakeProcess:
            returncode = None

            def __init__(self) -> None:
                self.terminated = False
                self.killed = False

            def communicate(self, *, timeout: int) -> tuple[str, None]:
                raise subprocess.TimeoutExpired(["codex"], timeout)

            def terminate(self) -> None:
                self.terminated = True

            def kill(self) -> None:
                self.killed = True

            def wait(self, timeout: int | None = None) -> int:
                return 0

        process = FakeProcess()
        with (
            patch("scripts.sympohy.runner.subprocess.Popen", return_value=process),
            self.assertRaises(_RunLockedError),
        ):
            _check_output_with_heartbeat(
                ["codex"],
                cwd=Path("/tmp/worktree"),
                heartbeat=lambda: (_ for _ in ()).throw(_RunLockedError("lost lock")),
            )

        self.assertTrue(process.terminated)
        self.assertFalse(process.killed)

    def test_run_command_terminates_child_when_heartbeat_loses_lock(self) -> None:
        class FakeProcess:
            def __init__(self) -> None:
                self.terminated = False
                self.killed = False

            def wait(self, timeout: int | None = None) -> int:
                if self.terminated:
                    return 0
                raise subprocess.TimeoutExpired(["task"], timeout)

            def poll(self) -> int | None:
                if self.terminated:
                    return 0
                return None

            def terminate(self) -> None:
                self.terminated = True

            def kill(self) -> None:
                self.killed = True

        process = FakeProcess()
        with (
            patch("scripts.sympohy.runner.subprocess.Popen", return_value=process),
            self.assertRaises(_RunLockedError),
        ):
            _run_command_with_heartbeat(
                ["task", "ci"],
                cwd=Path("/tmp/worktree"),
                heartbeat=lambda: (_ for _ in ()).throw(_RunLockedError("lost lock")),
            )

        self.assertTrue(process.terminated)
        self.assertFalse(process.killed)

    def test_pull_request_exists_blocks_duplicate_head_prs(self) -> None:
        result = subprocess.CompletedProcess(
            [],
            0,
            stdout=json.dumps([{"number": 83}, {"number": 84}]),
        )
        with (
            patch("scripts.sympohy.runner.subprocess.run", return_value=result),
            self.assertRaises(_AmbiguousPullRequestError),
        ):
            _pull_request_exists(branch="issue-82-sympohy", cwd=Path("/tmp/worktree"))

    def test_pull_request_exists_accepts_single_head_pr(self) -> None:
        result = subprocess.CompletedProcess([], 0, stdout=json.dumps([{"number": 83}]))
        with patch("scripts.sympohy.runner.subprocess.run", return_value=result):
            exists = _pull_request_exists(
                branch="issue-82-sympohy",
                cwd=Path("/tmp/worktree"),
            )

        self.assertTrue(exists)

    def test_pull_request_exists_ignores_closed_pr_for_head_branch(self) -> None:
        result = subprocess.CompletedProcess([], 0, stdout=json.dumps([]))
        with patch("scripts.sympohy.runner.subprocess.run", return_value=result) as run:
            exists = _pull_request_exists(
                branch="issue-82-sympohy",
                cwd=Path("/tmp/worktree"),
            )

        self.assertFalse(exists)
        run.assert_called_once()

    def test_pull_request_exists_fallback_requires_open_matching_head(self) -> None:
        list_failure = subprocess.CompletedProcess([], 1, stdout="")
        closed_pr = subprocess.CompletedProcess(
            [],
            0,
            stdout=json.dumps({"headRefName": "issue-82-sympohy", "state": "CLOSED"}),
        )
        with patch(
            "scripts.sympohy.runner.subprocess.run",
            side_effect=[list_failure, closed_pr],
        ):
            exists = _pull_request_exists(
                branch="issue-82-sympohy",
                cwd=Path("/tmp/worktree"),
            )

        self.assertFalse(exists)

    def test_pull_request_merged_detects_merged_pull_request(self) -> None:
        result = subprocess.CompletedProcess(
            [],
            0,
            stdout=json.dumps(
                {
                    "state": "MERGED",
                    "mergedAt": "2026-06-25T10:00:00Z",
                }
            ),
        )
        with patch("scripts.sympohy.runner.subprocess.run", return_value=result) as run:
            merged = _pull_request_merged(cwd=Path("/tmp/worktree"))

        self.assertTrue(merged)
        run.assert_called_once_with(
            ["gh", "pr", "view", "--json", "state,mergedAt"],
            cwd=Path("/tmp/worktree"),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )

    def test_pull_request_merged_returns_false_for_open_pull_request(self) -> None:
        result = subprocess.CompletedProcess(
            [],
            0,
            stdout=json.dumps({"state": "OPEN", "mergedAt": None}),
        )
        with patch("scripts.sympohy.runner.subprocess.run", return_value=result):
            merged = _pull_request_merged(cwd=Path("/tmp/worktree"))

        self.assertFalse(merged)

    def test_pull_request_merged_returns_false_for_closed_unmerged_pull_request(
        self,
    ) -> None:
        result = subprocess.CompletedProcess(
            [],
            0,
            stdout=json.dumps({"state": "CLOSED", "mergedAt": None}),
        )
        with patch("scripts.sympohy.runner.subprocess.run", return_value=result):
            merged = _pull_request_merged(cwd=Path("/tmp/worktree"))

        self.assertFalse(merged)

    def test_pull_request_merged_returns_false_when_gh_view_fails(self) -> None:
        result = subprocess.CompletedProcess([], 1, stdout="")
        with patch("scripts.sympohy.runner.subprocess.run", return_value=result):
            merged = _pull_request_merged(cwd=Path("/tmp/worktree"))

        self.assertFalse(merged)

    def test_pull_request_merged_returns_false_for_invalid_json(self) -> None:
        result = subprocess.CompletedProcess([], 0, stdout="{not json")
        with patch("scripts.sympohy.runner.subprocess.run", return_value=result):
            merged = _pull_request_merged(cwd=Path("/tmp/worktree"))

        self.assertFalse(merged)

    def test_pull_request_merged_returns_false_without_merged_at(self) -> None:
        result = subprocess.CompletedProcess(
            [],
            0,
            stdout=json.dumps({"state": "MERGED", "mergedAt": None}),
        )
        with patch("scripts.sympohy.runner.subprocess.run", return_value=result):
            merged = _pull_request_merged(cwd=Path("/tmp/worktree"))

        self.assertFalse(merged)

    def test_run_issue_progresses_through_hooks_commit_push_review_final_verifier_merge(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            worktree = config.worktree_root / "issue-82"
            issue = Issue(
                number=82,
                title="Complete final verifier flow",
                body="""
## AC
- [ ] implement and verify the change

## DoD
- [ ] open, review, verify, and merge the PR
""",
                labels=("enhancement",),
                comments=(),
            )
            events: list[str] = []

            def ensure_worktree(
                _issue: Issue,
                _config: SympohyConfig,
                *,
                recover: bool,
            ) -> Path:
                self.assertFalse(recover)
                worktree.mkdir(parents=True)
                events.append("ensure_worktree")
                return worktree

            def codex_json(
                _prompts: list[str],
                *,
                log_path: Path,
                **_kwargs: object,
            ) -> dict[str, object]:
                events.append(log_path.name)
                if log_path.name == "plan.json":
                    return {
                        "logical_steps": [
                            {"name": "write code"},
                            {"name": "add tests"},
                        ]
                    }
                if log_path.name == "final-verifier-1.json":
                    return {
                        "acceptance_criteria_satisfied": True,
                        "definition_of_done_satisfied": True,
                        "merge_recommendation": "merge",
                        "findings": [],
                    }
                raise AssertionError(f"unexpected codex JSON log: {log_path}")

            def codex_text(
                _prompts: list[str],
                *,
                log_path: Path,
                **_kwargs: object,
            ) -> str:
                events.append(log_path.name)
                return ""

            def run_hooks(
                _hooks: tuple[str, ...],
                _retry_max_attempts: int,
                _cwd: Path,
                _log_dir: Path,
                **kwargs: object,
            ) -> int:
                events.append(f"hooks:{kwargs['logical_step']}")
                return 0

            def commit_all_if_new(subject: str, **_kwargs: object) -> bool:
                events.append(subject)
                return True

            def push_pr(**_kwargs: object) -> None:
                events.append("push_pr")

            def review_fix_loop(*_args: object, **_kwargs: object) -> int:
                events.append("review")
                return 0

            def check_call_with_heartbeat(command: list[str], **_kwargs: object) -> None:
                events.append(" ".join(command))

            def check_call(command: list[str], **_kwargs: object) -> None:
                events.append(" ".join(command))

            def final_verifier_comment(
                pull_request_number: str,
                _body: str,
                **_kwargs: object,
            ) -> None:
                events.append(f"comment:{pull_request_number}")

            with ExitStack() as stack:
                stack.enter_context(
                    patch("scripts.sympohy.runner.fetch_issue", return_value=issue)
                )
                stack.enter_context(
                    patch("scripts.sympohy.runner._branch_exists", return_value=False)
                )
                stack.enter_context(
                    patch(
                        "scripts.sympohy.runner._remote_branch_exists",
                        return_value=False,
                    )
                )
                stack.enter_context(
                    patch(
                        "scripts.sympohy.runner.ensure_worktree",
                        side_effect=ensure_worktree,
                    )
                )
                stack.enter_context(
                    patch(
                        "scripts.sympohy.runner._current_branch",
                        return_value="issue-82-sympohy",
                    )
                )
                stack.enter_context(
                    patch(
                        "scripts.sympohy.runner.subprocess.check_output",
                        return_value="issue-82-sympohy\n",
                    )
                )
                stack.enter_context(
                    patch("scripts.sympohy.runner._codex_json", side_effect=codex_json)
                )
                stack.enter_context(
                    patch("scripts.sympohy.runner._codex_text", side_effect=codex_text)
                )
                stack.enter_context(
                    patch("scripts.sympohy.runner._commit_subjects", return_value=[])
                )
                stack.enter_context(
                    patch(
                        "scripts.sympohy.runner._branch_has_commits",
                        return_value=False,
                    )
                )
                stack.enter_context(
                    patch("scripts.sympohy.runner._run_hooks", side_effect=run_hooks)
                )
                stack.enter_context(
                    patch(
                        "scripts.sympohy.runner._commit_all_if_new",
                        side_effect=commit_all_if_new,
                    )
                )
                stack.enter_context(
                    patch(
                        "scripts.sympohy.runner._push_branch_and_ensure_draft_pull_request",
                        side_effect=push_pr,
                    )
                )
                stack.enter_context(
                    patch(
                        "scripts.sympohy.runner._review_fix_loop",
                        side_effect=review_fix_loop,
                    )
                )
                stack.enter_context(
                    patch(
                        "scripts.sympohy.runner._pull_request_merged",
                        return_value=False,
                    )
                )
                stack.enter_context(
                    patch(
                        "scripts.sympohy.runner._resolve_pull_request_number",
                        return_value="99",
                    )
                )
                comment = stack.enter_context(
                    patch(
                        "scripts.sympohy.runner.comment",
                        side_effect=final_verifier_comment,
                    )
                )
                stack.enter_context(
                    patch(
                        "scripts.sympohy.runner._check_call_with_heartbeat",
                        side_effect=check_call_with_heartbeat,
                    )
                )
                stack.enter_context(
                    patch(
                        "scripts.sympohy.runner.subprocess.check_call",
                        side_effect=check_call,
                    )
                )
                set_issue_state = stack.enter_context(
                    patch("scripts.sympohy.runner.set_issue_state")
                )
                result = run_issue("#82", config)

            log_dir = config.run_log_root / "issue-82"
            final_state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))
            final_verifier = json.loads(
                (log_dir / "final-verifier-1.json").read_text(encoding="utf-8")
            )
            compatibility_final_verifier = json.loads(
                (log_dir / "final-verifier.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result, 0)
        self.assertEqual(
            events,
            [
                "ensure_worktree",
                "push_pr",
                "plan.json",
                "implement-1.log",
                "hooks:1",
                "#82 feat(sympohy): implement logical step 1",
                "implement-2.log",
                "hooks:2",
                "#82 feat(sympohy): implement logical step 2",
                "push_pr",
                "review",
                "final-verifier-1.json",
                "comment:99",
                "gh pr ready",
                "gh pr checks --watch",
                "gh pr merge --squash --delete-branch",
                f"git worktree remove {worktree}",
                "gh issue close #82",
            ],
        )
        self.assertEqual(final_verifier["merge_recommendation"], "merge")
        self.assertEqual(compatibility_final_verifier, final_verifier)
        self.assertEqual(final_state["status"], "done")
        self.assertEqual(final_state["phase"], "finalize")
        self.assertEqual(
            final_state["last_known_progress"]["message"],
            "merged pull request and removed worktree",
        )
        comment.assert_called_once()
        self.assertIn("final-verifier-1.json", comment.call_args.args[1])
        state_transitions = [
            (call.kwargs["status"], call.kwargs["phase"])
            for call in set_issue_state.call_args_list
        ]
        self.assertIn(("sympohy:pending", "triage"), state_transitions)
        self.assertIn(("sympohy:running", "implement"), state_transitions)
        self.assertIn(("sympohy:done", "finalize"), state_transitions)

    def test_final_merge_github_commands_refresh_heartbeat(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / "worktrees" / "issue-82"
            log_dir = root / "runs" / "issue-82"
            worktree.mkdir(parents=True)
            log_dir.mkdir(parents=True)
            issue = Issue(
                number=82,
                title="Merge stale-safe PR",
                body="",
                labels=("sympohy:running", "sympohy:phase:finalize"),
                comments=(),
            )
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
                worktree=worktree,
                branch="issue-82-sympohy",
            )

            with (
                patch(
                    "scripts.sympohy.runner._codex_json",
                    return_value={
                        "acceptance_criteria_satisfied": True,
                        "definition_of_done_satisfied": True,
                        "merge_recommendation": "merge",
                    },
                ) as codex_json,
                patch(
                    "scripts.sympohy.runner._run_command_with_heartbeat",
                    return_value=0,
                ) as run_command,
                patch("scripts.sympohy.runner._pull_request_merged", return_value=False),
                patch(
                    "scripts.sympohy.runner._resolve_pull_request_number",
                    return_value="99",
                ),
                patch("scripts.sympohy.runner.comment") as comment,
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
                patch("scripts.sympohy.runner.set_issue_state"),
            ):
                result = _run_final_verifier_and_merge(
                    "#82",
                    issue,
                    self._config(root),
                    worktree,
                    log_dir,
                    state,
                    total_steps=3,
                )

        self.assertEqual(result, 0)
        comment.assert_called_once()
        self.assertEqual(comment.call_args.args[0], "99")
        self.assertIn("sympohy final verifier result", comment.call_args.args[1])
        self.assertIn("final-verifier-1.json", comment.call_args.args[1])
        self.assertIn('"merge_recommendation": "merge"', comment.call_args.args[1])
        final_verifier_prompt = codex_json.call_args.args[0][0]
        self.assertIn("findings as an array", final_verifier_prompt)
        self.assertIn('When merge_recommendation is "merge"', final_verifier_prompt)
        self.assertIn("findings must be an empty array", final_verifier_prompt)
        self.assertIn('When merge_recommendation is "block"', final_verifier_prompt)
        self.assertIn("findings must be a non-empty array", final_verifier_prompt)
        for field in ("kind", "summary", "evidence", "suggested_fix"):
            self.assertIn(field, final_verifier_prompt)
        for kind in (
            "acceptance_criteria",
            "definition_of_done",
            "verification",
            "reviewability",
            "other",
        ):
            self.assertIn(kind, final_verifier_prompt)
        heartbeat_commands = [call.args[0] for call in run_command.call_args_list]
        self.assertEqual(
            heartbeat_commands,
            [
                ["gh", "pr", "ready"],
                ["gh", "pr", "checks", "--watch"],
                ["gh", "pr", "merge", "--squash", "--delete-branch"],
            ],
        )
        self.assertTrue(
            all(
                call.kwargs["heartbeat"] == state.heartbeat
                for call in run_command.call_args_list
            )
        )
        check_call.assert_any_call(["git", "worktree", "remove", str(worktree)])
        check_call.assert_any_call(["gh", "issue", "close", "#82"])

    def test_final_verifier_block_routes_valid_findings_to_fix(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / "worktrees" / "issue-82"
            log_dir = root / "runs" / "issue-82"
            worktree.mkdir(parents=True)
            log_dir.mkdir(parents=True)
            issue = Issue(
                number=82,
                title="Fix final verifier findings",
                body="",
                labels=("sympohy:running", "sympohy:phase:finalize"),
                comments=(),
            )
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
                worktree=worktree,
                branch="issue-82-sympohy",
            )
            (log_dir / "review-1.json").write_text(
                '{"findings":[]}\n',
                encoding="utf-8",
            )
            events: list[str] = []
            verifier_responses = [
                {
                    "acceptance_criteria_satisfied": False,
                    "definition_of_done_satisfied": True,
                    "merge_recommendation": "block",
                    "findings": [
                        {
                            "kind": "acceptance_criteria",
                            "summary": "resume state is not validated",
                            "evidence": "state.json accepts missing fix_source",
                            "suggested_fix": "persist fix_source for verifier fixes",
                        }
                    ],
                },
                {
                    "acceptance_criteria_satisfied": True,
                    "definition_of_done_satisfied": True,
                    "merge_recommendation": "merge",
                },
            ]

            def codex_json(
                _prompts: list[str],
                *,
                log_path: Path,
                **_kwargs: object,
            ) -> dict[str, object]:
                events.append(log_path.name)
                response = verifier_responses.pop(0)
                log_path.write_text(
                    json.dumps(response, ensure_ascii=False, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                return response

            def check_call_with_heartbeat(
                command: list[str],
                **_kwargs: object,
            ) -> None:
                events.append(" ".join(command))

            def review_fix_loop(*_args: object, **kwargs: object) -> int:
                events.append(f"review:{kwargs['start_round']}")
                return 0

            with (
                patch("scripts.sympohy.runner._pull_request_merged", return_value=False),
                patch(
                    "scripts.sympohy.runner._codex_json",
                    side_effect=codex_json,
                ) as codex_json_mock,
                patch(
                    "scripts.sympohy.runner._worktree_has_changes",
                    side_effect=[False, True],
                ),
                patch("scripts.sympohy.runner._commit_subject_exists", return_value=False),
                patch("scripts.sympohy.runner._codex_text", return_value="") as codex_text,
                patch("scripts.sympohy.runner._run_hooks", return_value=0) as run_hooks,
                patch(
                    "scripts.sympohy.runner._commit_all_if_new",
                    return_value=True,
                ) as commit_all_if_new,
                patch(
                    "scripts.sympohy.runner._check_call_with_heartbeat",
                    side_effect=check_call_with_heartbeat,
                ),
                patch(
                    "scripts.sympohy.runner._review_fix_loop",
                    side_effect=review_fix_loop,
                ) as review_fix_loop_mock,
                patch(
                    "scripts.sympohy.runner._resolve_pull_request_number",
                    return_value="99",
                ),
                patch("scripts.sympohy.runner.comment") as comment,
                patch("scripts.sympohy.runner.subprocess.check_call"),
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
            ):
                result = _run_final_verifier_and_merge(
                    "#82",
                    issue,
                    self._config(root),
                    worktree,
                    log_dir,
                    state,
                    total_steps=3,
                )

            final_state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))
            first_attempt = json.loads(
                (log_dir / "final-verifier-1.json").read_text(encoding="utf-8")
            )
            second_attempt = json.loads(
                (log_dir / "final-verifier-2.json").read_text(encoding="utf-8")
            )
            latest_attempt = json.loads(
                (log_dir / "final-verifier.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result, 0)
        self.assertEqual(
            [
                call.kwargs["log_path"].name
                for call in codex_json_mock.call_args_list
            ],
            ["final-verifier-1.json", "final-verifier-2.json"],
        )
        self.assertEqual(first_attempt["merge_recommendation"], "block")
        self.assertEqual(second_attempt["merge_recommendation"], "merge")
        self.assertEqual(latest_attempt, second_attempt)
        self.assertEqual(comment.call_count, 2)
        self.assertEqual(
            [call.args[0] for call in comment.call_args_list],
            ["99", "99"],
        )
        self.assertIn("final-verifier-1.json", comment.call_args_list[0].args[1])
        self.assertIn("final-verifier-2.json", comment.call_args_list[1].args[1])
        self.assertIn("resume state is not validated", comment.call_args_list[0].args[1])
        self.assertIn(
            '"merge_recommendation": "merge"',
            comment.call_args_list[1].args[1],
        )
        self.assertEqual(
            events,
            [
                "final-verifier-1.json",
                "git push",
                "review:2",
                "final-verifier-2.json",
                "gh pr ready",
                "gh pr checks --watch",
                "gh pr merge --squash --delete-branch",
            ],
        )
        review_fix_loop_mock.assert_called_once()
        self.assertEqual(review_fix_loop_mock.call_args.kwargs["start_round"], 2)
        set_issue_state.assert_any_call(
            "#82",
            current_labels=(),
            status="sympohy:running",
            phase="fix",
            cwd=worktree,
        )
        codex_text.assert_called_once()
        self.assertIn(
            "resume state is not validated",
            codex_text.call_args.args[0][1],
        )
        run_hooks.assert_called_once()
        commit_all_if_new.assert_called_once_with(
            "#82 fix(sympohy): resolve final verifier finding 1",
            cwd=worktree,
            base_branch="main",
            existing_subjects=None,
        )
        self.assertEqual(final_state["status"], "done")
        self.assertEqual(
            final_state["last_known_progress"]["message"],
            "merged pull request and removed worktree",
        )

    def test_final_verifier_blocks_when_verifier_returns_manual_block(self) -> None:
        def retry_response(summary: str) -> dict[str, object]:
            return {
                "status": "retry",
                "acceptance_criteria_satisfied": False,
                "definition_of_done_satisfied": True,
                "merge_recommendation": "block",
                "findings": [
                    {
                        "kind": "acceptance_criteria",
                        "summary": summary,
                        "evidence": "final verifier still finds a blocker",
                        "suggested_fix": "fix the remaining blocker",
                    }
                ],
            }

        manual_block_response = {
            "status": "block",
            "acceptance_criteria_satisfied": False,
            "definition_of_done_satisfied": True,
            "merge_recommendation": "block",
            "findings": [
                {
                    "kind": "other",
                    "summary": "manual decision required",
                    "evidence": "final verifier cannot determine a safe fix",
                    "suggested_fix": "ask a human owner to decide",
                }
            ],
        }

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / "worktrees" / "issue-82"
            log_dir = root / "runs" / "issue-82"
            worktree.mkdir(parents=True)
            log_dir.mkdir(parents=True)
            issue = Issue(
                number=82,
                title="Stop final verifier fix loop",
                body="",
                labels=("sympohy:running", "sympohy:phase:finalize"),
                comments=(),
            )
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
                worktree=worktree,
                branch="issue-82-sympohy",
            )

            with (
                patch("scripts.sympohy.runner._pull_request_merged", return_value=False),
                patch(
                    "scripts.sympohy.runner._codex_json",
                    side_effect=[
                        retry_response("first blocker"),
                        manual_block_response,
                    ],
                ) as codex_json,
                patch(
                    "scripts.sympohy.runner._run_final_verifier_fix_round",
                    return_value=1,
                ) as run_final_verifier_fix_round,
                patch(
                    "scripts.sympohy.runner._review_fix_loop",
                    return_value=0,
                ) as review_fix_loop,
                patch(
                    "scripts.sympohy.runner._resolve_pull_request_number",
                    return_value="99",
                ),
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                result = _run_final_verifier_and_merge(
                    "#82",
                    issue,
                    self._config(root),
                    worktree,
                    log_dir,
                    state,
                    total_steps=3,
                )

            final_state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(result, 2)
        self.assertEqual(codex_json.call_count, 2)
        self.assertEqual(run_final_verifier_fix_round.call_count, 1)
        self.assertEqual(review_fix_loop.call_count, 1)
        self.assertEqual(
            [call.args[0] for call in comment.call_args_list[:2]],
            ["99"] * 2,
        )
        self.assertIn("first blocker", comment.call_args_list[0].args[1])
        self.assertIn("manual decision required", comment.call_args_list[1].args[1])
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:finalize"),
            status="sympohy:blocked",
            phase="finalize",
            cwd=worktree,
        )
        self.assertIn(
            "final verifier requested manual block",
            comment.call_args.args[1],
        )
        self.assertEqual(final_state["status"], "blocked")
        self.assertEqual(final_state["last_known_progress"]["attempts"], 2)

    def test_final_verifier_block_with_invalid_findings_blocks_issue(self) -> None:
        invalid_responses = (
            {
                "acceptance_criteria_satisfied": False,
                "definition_of_done_satisfied": True,
                "merge_recommendation": "block",
            },
            {
                "acceptance_criteria_satisfied": False,
                "definition_of_done_satisfied": True,
                "merge_recommendation": "block",
                "findings": [],
            },
            {
                "acceptance_criteria_satisfied": False,
                "definition_of_done_satisfied": True,
                "merge_recommendation": "block",
                "findings": [{"kind": "verification", "summary": "missing fields"}],
            },
        )

        for response in invalid_responses:
            with self.subTest(response=response), TemporaryDirectory() as tmp:
                root = Path(tmp)
                worktree = root / "worktrees" / "issue-82"
                log_dir = root / "runs" / "issue-82"
                worktree.mkdir(parents=True)
                log_dir.mkdir(parents=True)
                issue = Issue(
                    number=82,
                    title="Block invalid final verifier findings",
                    body="",
                    labels=("sympohy:running", "sympohy:phase:finalize"),
                    comments=(),
                )
                state = _RunStateWriter(
                    issue_number=82,
                    log_dir=log_dir,
                    base_branch="main",
                    worktree=worktree,
                    branch="issue-82-sympohy",
                )

                with (
                    patch("scripts.sympohy.runner._pull_request_merged", return_value=False),
                    patch("scripts.sympohy.runner._codex_json", return_value=response),
                    patch(
                        "scripts.sympohy.runner._resolve_pull_request_number",
                        return_value="99",
                    ),
                    patch("scripts.sympohy.runner._codex_text") as codex_text,
                    patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                    patch("scripts.sympohy.runner.comment") as comment,
                ):
                    result = _run_final_verifier_and_merge(
                        "#82",
                        issue,
                        self._config(root),
                        worktree,
                        log_dir,
                        state,
                        total_steps=3,
                    )

                final_state = json.loads(
                    (log_dir / "state.json").read_text(encoding="utf-8")
                )
                attempt_artifact = json.loads(
                    (log_dir / "final-verifier-1.json").read_text(encoding="utf-8")
                )
                compatibility_artifact = json.loads(
                    (log_dir / "final-verifier.json").read_text(encoding="utf-8")
                )

            self.assertEqual(result, 2)
            codex_text.assert_not_called()
            expected_artifact = {**response, "status": "retry"}
            self.assertEqual(attempt_artifact, expected_artifact)
            self.assertEqual(compatibility_artifact, expected_artifact)
            set_issue_state.assert_called_once_with(
                "#82",
                current_labels=("sympohy:running", "sympohy:phase:finalize"),
                status="sympohy:blocked",
                phase="finalize",
                cwd=worktree,
            )
            self.assertIn("invalid findings", comment.call_args.args[1])
            self.assertEqual(final_state["status"], "blocked")

    def test_final_verifier_blocks_when_fix_attempt_limit_is_exceeded(self) -> None:
        def verifier_response(summary: str) -> dict[str, object]:
            return {
                "status": "retry",
                "acceptance_criteria_satisfied": False,
                "definition_of_done_satisfied": True,
                "merge_recommendation": "block",
                "findings": [
                    {
                        "kind": "acceptance_criteria",
                        "summary": summary,
                        "evidence": "final verifier still finds a blocker",
                        "suggested_fix": "fix the remaining gap",
                    }
                ],
            }

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / "worktrees" / "issue-82"
            log_dir = root / "runs" / "issue-82"
            worktree.mkdir(parents=True)
            log_dir.mkdir(parents=True)
            issue = Issue(
                number=82,
                title="Stop final verifier fix loop",
                body="",
                labels=("sympohy:running", "sympohy:phase:finalize"),
                comments=(),
            )
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
                worktree=worktree,
                branch="issue-82-sympohy",
            )
            config = SympohyConfig(
                max_workers=1,
                base_branch="main",
                worktree_root=root / "worktrees",
                run_log_root=root / "runs",
                stale_status_after_minutes=30,
                hooks=("task ci",),
                review_max_rounds=1,
                retry_max_attempts=3,
                final_verifier_fix_max_attempts=2,
                stage_gate_command=None,
            )

            with (
                patch("scripts.sympohy.runner._pull_request_merged", return_value=False),
                patch(
                    "scripts.sympohy.runner._codex_json",
                    side_effect=[
                        verifier_response("first gap"),
                        verifier_response("second gap"),
                        verifier_response("third gap"),
                    ],
                ),
                patch(
                    "scripts.sympohy.runner._run_final_verifier_fix_round",
                    return_value=1,
                ) as run_final_verifier_fix_round,
                patch(
                    "scripts.sympohy.runner._review_fix_loop",
                    return_value=0,
                ) as review_fix_loop,
                patch(
                    "scripts.sympohy.runner._resolve_pull_request_number",
                    return_value="99",
                ),
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                result = _run_final_verifier_and_merge(
                    "#82",
                    issue,
                    config,
                    worktree,
                    log_dir,
                    state,
                    total_steps=3,
                )

            final_state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(result, 2)
        self.assertEqual(run_final_verifier_fix_round.call_count, 2)
        self.assertEqual(review_fix_loop.call_count, 2)
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:finalize"),
            status="sympohy:blocked",
            phase="finalize",
            cwd=worktree,
        )
        self.assertIn(
            "final_verifier_fix_max_attempts (2)",
            comment.call_args.args[1],
        )
        self.assertEqual(final_state["status"], "blocked")
        self.assertEqual(final_state["last_known_progress"]["attempts"], 3)

    def test_final_verifier_fix_blocks_when_codex_makes_no_changes(self) -> None:
        verifier_response = {
            "acceptance_criteria_satisfied": False,
            "definition_of_done_satisfied": True,
            "merge_recommendation": "block",
            "findings": [
                {
                    "kind": "verification",
                    "summary": "missing regression test",
                    "evidence": "no test covers final verifier resume",
                    "suggested_fix": "add the missing test",
                }
            ],
        }

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cwd = root / "worktrees" / "issue-82"
            log_dir = root / "runs" / "issue-82"
            cwd.mkdir(parents=True)
            log_dir.mkdir(parents=True)
            issue = Issue(
                number=82,
                title="No-op final verifier fix",
                body="",
                labels=("sympohy:running", "sympohy:phase:fix"),
                comments=(),
            )
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
                worktree=cwd,
                branch="issue-82-sympohy",
            )

            with (
                patch(
                    "scripts.sympohy.runner._worktree_has_changes",
                    side_effect=[False, False],
                ),
                patch("scripts.sympohy.runner._commit_subject_exists", return_value=False),
                patch("scripts.sympohy.runner._codex_text", return_value="") as codex_text,
                patch("scripts.sympohy.runner._run_hooks") as run_hooks,
                patch("scripts.sympohy.runner._commit_all_if_new") as commit_all_if_new,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                config = self._config(root)
                result = _run_final_verifier_fix_round(
                    "#82",
                    issue,
                    config,
                    cwd,
                    log_dir,
                    state,
                    findings=parse_final_verifier_block_findings(verifier_response),
                    fix_attempt=1,
                    total_steps=3,
                )

            final_state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(result, 2)
        codex_text.assert_called_once()
        run_hooks.assert_not_called()
        commit_all_if_new.assert_not_called()
        set_issue_state.assert_any_call(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:fix"),
            status="sympohy:blocked",
            phase="fix",
            cwd=cwd,
        )
        self.assertIn("produced no changes", comment.call_args.args[1])
        self.assertIn(
            "#82 fix(sympohy): resolve final verifier finding 1",
            comment.call_args.args[1],
        )
        self.assertEqual(final_state["status"], "blocked")

    def test_final_verifier_existing_fix_commit_blocks_when_hooks_fail(self) -> None:
        verifier_response = {
            "acceptance_criteria_satisfied": False,
            "definition_of_done_satisfied": True,
            "merge_recommendation": "block",
            "findings": [
                {
                    "kind": "verification",
                    "summary": "existing fix must be verified before push",
                    "evidence": "final verifier fix commit already exists",
                    "suggested_fix": "run hooks before pushing the existing fix",
                }
            ],
        }

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cwd = root / "worktrees" / "issue-82"
            log_dir = root / "runs" / "issue-82"
            cwd.mkdir(parents=True)
            log_dir.mkdir(parents=True)
            issue = Issue(
                number=82,
                title="Verify existing final verifier fix",
                body="",
                labels=("sympohy:running", "sympohy:phase:fix"),
                comments=(),
            )
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
                worktree=cwd,
                branch="issue-82-sympohy",
            )

            with (
                patch("scripts.sympohy.runner._worktree_has_changes", return_value=False),
                patch("scripts.sympohy.runner._commit_subject_exists", return_value=True),
                patch("scripts.sympohy.runner._run_hooks", return_value=7) as run_hooks,
                patch("scripts.sympohy.runner._check_call_with_heartbeat") as check_call,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                config = self._config(root)
                result = _run_final_verifier_fix_round(
                    "#82",
                    issue,
                    config,
                    cwd,
                    log_dir,
                    state,
                    findings=parse_final_verifier_block_findings(verifier_response),
                    fix_attempt=1,
                    total_steps=3,
                    from_resume=True,
                )

            final_state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(result, 2)
        run_hooks.assert_called_once_with(
            ("task ci",),
            3,
            cwd,
            log_dir,
            config=config,
            state=state,
        )
        check_call.assert_not_called()
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:hooks"),
            status="sympohy:blocked",
            phase="hooks",
            cwd=cwd,
        )
        self.assertIn(
            "verification hooks still failed after final verifier fix",
            comment.call_args.args[1],
        )
        self.assertEqual(final_state["phase"], "hooks")
        self.assertEqual(final_state["status"], "blocked")

    def test_final_verifier_fix_resume_reruns_review_before_finalize(self) -> None:
        verifier_response = {
            "acceptance_criteria_satisfied": False,
            "definition_of_done_satisfied": True,
            "merge_recommendation": "block",
            "findings": [
                {
                    "kind": "acceptance_criteria",
                    "summary": "resume must re-review verifier fixes",
                    "evidence": "final verifier fix resume has pushed a new commit",
                    "suggested_fix": "rerun adversarial review before final verifier",
                }
            ],
        }

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cwd = root / "worktrees" / "issue-82"
            log_dir = root / "runs" / "issue-82"
            cwd.mkdir(parents=True)
            log_dir.mkdir(parents=True)
            (log_dir / "final-verifier-1.json").write_text(
                json.dumps(verifier_response),
                encoding="utf-8",
            )
            (log_dir / "review-1.json").write_text(
                '{"findings":[]}\n',
                encoding="utf-8",
            )
            issue = Issue(
                number=82,
                title="Resume verifier fix through review",
                body="",
                labels=("sympohy:running", "sympohy:phase:fix"),
                comments=(),
            )
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
                worktree=cwd,
                branch="issue-82-sympohy",
            )

            with (
                patch(
                    "scripts.sympohy.runner._run_final_verifier_fix_round",
                    return_value=1,
                ) as run_final_verifier_fix_round,
                patch(
                    "scripts.sympohy.runner._review_fix_loop",
                    return_value=0,
                ) as review_fix_loop,
            ):
                result = _resume_fix_phase(
                    "#82",
                    issue,
                    self._config(root),
                    cwd,
                    log_dir,
                    state,
                    previous_state={
                        "last_known_progress": {
                            "fix_source": "final_verifier",
                            "final_verifier_fix_attempt": 1,
                            "total_logical_steps": 3,
                        }
                    },
                )

        self.assertEqual(result, 0)
        run_final_verifier_fix_round.assert_called_once()
        self.assertTrue(run_final_verifier_fix_round.call_args.kwargs["from_resume"])
        self.assertEqual(run_final_verifier_fix_round.call_args.kwargs["total_steps"], 3)
        review_fix_loop.assert_called_once()
        self.assertEqual(review_fix_loop.call_args.kwargs["start_round"], 2)

    def test_final_verifier_fix_resume_blocks_dirty_worktree_before_rerun(
        self,
    ) -> None:
        verifier_response = {
            "acceptance_criteria_satisfied": False,
            "definition_of_done_satisfied": True,
            "merge_recommendation": "block",
            "findings": [
                {
                    "kind": "acceptance_criteria",
                    "summary": "state is incomplete",
                    "evidence": "resume progress is missing fix source handling",
                    "suggested_fix": "resume the verifier fix attempt",
                }
            ],
        }

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cwd = root / "worktrees" / "issue-82"
            log_dir = root / "runs" / "issue-82"
            cwd.mkdir(parents=True)
            log_dir.mkdir(parents=True)
            (log_dir / "final-verifier-1.json").write_text(
                json.dumps(verifier_response),
                encoding="utf-8",
            )
            issue = Issue(
                number=82,
                title="Resume final verifier fix",
                body="",
                labels=("sympohy:running", "sympohy:phase:fix"),
                comments=(),
            )
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
                worktree=cwd,
                branch="issue-82-sympohy",
            )

            with (
                patch("scripts.sympohy.runner._worktree_has_changes", return_value=True),
                patch(
                    "scripts.sympohy.runner._worktree_status",
                    return_value=" M scripts/sympohy/runner.py\n",
                ),
                patch(
                    "scripts.sympohy.runner._commit_subject_exists",
                    return_value=False,
                ) as commit_subject_exists,
                patch("scripts.sympohy.runner._codex_text") as codex_text,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                result = _resume_fix_phase(
                    "#82",
                    issue,
                    self._config(root),
                    cwd,
                    log_dir,
                    state,
                    previous_state={
                        "last_known_progress": {
                            "fix_source": "final_verifier",
                            "final_verifier_fix_attempt": 1,
                            "total_logical_steps": 3,
                        }
                    },
                )

            final_state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(result, 2)
        commit_subject_exists.assert_not_called()
        codex_text.assert_not_called()
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:fix"),
            status="sympohy:blocked",
            phase="fix",
            cwd=cwd,
        )
        self.assertIn(
            "final verifier fix phase worktree has uncommitted changes during resume",
            comment.call_args.args[1],
        )
        self.assertEqual(final_state["status"], "blocked")
        self.assertEqual(final_state["last_recovery"]["event"], "unsafe_recovery_blocked")

    def test_merge_resume_reconciles_already_merged_pull_request(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / "worktrees" / "issue-82"
            log_dir = root / "runs" / "issue-82"
            worktree.mkdir(parents=True)
            log_dir.mkdir(parents=True)
            issue = Issue(
                number=82,
                title="Merge stale-safe PR",
                body="",
                labels=("sympohy:running", "sympohy:phase:finalize"),
                comments=(),
            )
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
                worktree=worktree,
                branch="issue-82-sympohy",
            )

            with (
                patch("scripts.sympohy.runner._pull_request_merged", return_value=True),
                patch(
                    "scripts.sympohy.runner._worktree_status",
                    return_value="",
                ),
                patch("scripts.sympohy.runner._codex_json") as codex_json,
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
            ):
                result = _run_final_verifier_and_merge(
                    "#82",
                    issue,
                    self._config(root),
                    worktree,
                    log_dir,
                    state,
                    total_steps=3,
                )

            final_state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        codex_json.assert_not_called()
        check_call.assert_any_call(["git", "worktree", "remove", str(worktree)])
        check_call.assert_any_call(["gh", "issue", "close", "#82"])
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:finalize"),
            status="sympohy:done",
            phase="finalize",
        )
        self.assertEqual(final_state["status"], "done")
        self.assertEqual(
            final_state["last_known_progress"]["message"],
            "reconciled already-merged pull request",
        )

    def test_late_phase_resume_short_circuits_already_merged_pull_request(self) -> None:
        for phase in ("review", "fix", "finalize"):
            with self.subTest(phase=phase), TemporaryDirectory() as tmp:
                root = Path(tmp)
                worktree = root / "worktrees" / "issue-82"
                log_dir = root / "runs" / "issue-82"
                worktree.mkdir(parents=True)
                log_dir.mkdir(parents=True)
                issue = Issue(
                    number=82,
                    title="Resume merged pull request",
                    body="",
                    labels=("sympohy:running", f"sympohy:phase:{phase}"),
                    comments=(),
                )
                state = _RunStateWriter(
                    issue_number=82,
                    log_dir=log_dir,
                    base_branch="main",
                    worktree=worktree,
                    branch="issue-82-sympohy",
                )

                with (
                    patch("scripts.sympohy.runner.ensure_worktree", return_value=worktree),
                    patch(
                        "scripts.sympohy.runner._current_branch",
                        return_value="issue-82-sympohy",
                    ),
                    patch("scripts.sympohy.runner._pull_request_merged", return_value=True),
                    patch(
                        "scripts.sympohy.runner._worktree_status",
                        return_value="",
                    ) as worktree_status,
                    patch("scripts.sympohy.runner._review_fix_loop") as review_fix_loop,
                    patch(
                        "scripts.sympohy.runner._run_final_verifier_and_merge"
                    ) as final_merge,
                    patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                    patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
                ):
                    result = _resume_late_phase(
                        "#82",
                        issue,
                        self._config(root),
                        log_dir,
                        state,
                        previous_state={
                            "last_known_progress": {"total_logical_steps": 3}
                        },
                        resume_from=phase,
                    )

                final_state = json.loads(
                    (log_dir / "state.json").read_text(encoding="utf-8")
                )

            self.assertEqual(result, 0)
            if phase in {"review", "finalize"}:
                worktree_status.assert_called_once_with(worktree)
            else:
                worktree_status.assert_not_called()
            review_fix_loop.assert_not_called()
            final_merge.assert_not_called()
            set_issue_state.assert_called_once_with(
                "#82",
                current_labels=("sympohy:running", "sympohy:phase:finalize"),
                status="sympohy:done",
                phase="finalize",
            )
            check_call.assert_any_call(["git", "worktree", "remove", str(worktree)])
            check_call.assert_any_call(["gh", "issue", "close", "#82"])
            self.assertEqual(final_state["status"], "done")
            self.assertEqual(
                final_state["last_known_progress"]["message"],
                "reconciled already-merged pull request",
            )

    def test_finalize_resume_on_merged_pull_request_skips_final_verifier(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / "worktrees" / "issue-82"
            log_dir = root / "runs" / "issue-82"
            worktree.mkdir(parents=True)
            log_dir.mkdir(parents=True)
            issue = Issue(
                number=82,
                title="Resume merged finalize flow",
                body="",
                labels=("sympohy:running", "sympohy:phase:finalize"),
                comments=(),
            )
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
                worktree=worktree,
                branch="issue-82-sympohy",
            )

            with (
                patch("scripts.sympohy.runner.ensure_worktree", return_value=worktree),
                patch(
                    "scripts.sympohy.runner._current_branch",
                    return_value="issue-82-sympohy",
                ),
                patch("scripts.sympohy.runner._pull_request_merged", return_value=True),
                patch(
                    "scripts.sympohy.runner._worktree_status",
                    return_value="",
                ),
                patch("scripts.sympohy.runner._codex_json") as codex_json,
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
            ):
                result = _resume_late_phase(
                    "#82",
                    issue,
                    self._config(root),
                    log_dir,
                    state,
                    previous_state={
                        "last_known_progress": {"total_logical_steps": 3}
                    },
                    resume_from="finalize",
                )

            final_state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        codex_json.assert_not_called()
        check_call.assert_any_call(["git", "worktree", "remove", str(worktree)])
        check_call.assert_any_call(["gh", "issue", "close", "#82"])
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:finalize"),
            status="sympohy:done",
            phase="finalize",
        )
        self.assertEqual(final_state["status"], "done")
        self.assertEqual(
            final_state["last_known_progress"]["message"],
            "reconciled already-merged pull request",
        )
        self.assertEqual(
            final_state["last_known_progress"]["completed_logical_steps"],
            3,
        )

    def test_late_phase_resume_blocks_dirty_worktree_before_merged_pr_reconcile(
        self,
    ) -> None:
        for phase in ("review", "finalize"):
            with self.subTest(phase=phase), TemporaryDirectory() as tmp:
                root = Path(tmp)
                worktree = root / "worktrees" / "issue-82"
                log_dir = root / "runs" / "issue-82"
                worktree.mkdir(parents=True)
                log_dir.mkdir(parents=True)
                issue = Issue(
                    number=82,
                    title="Dirty merged late phase",
                    body="",
                    labels=("sympohy:running", f"sympohy:phase:{phase}"),
                    comments=(),
                )
                state = _RunStateWriter(
                    issue_number=82,
                    log_dir=log_dir,
                    base_branch="main",
                    worktree=worktree,
                    branch="issue-82-sympohy",
                )

                with (
                    patch("scripts.sympohy.runner.ensure_worktree", return_value=worktree),
                    patch(
                        "scripts.sympohy.runner._current_branch",
                        return_value="issue-82-sympohy",
                    ),
                    patch(
                        "scripts.sympohy.runner._worktree_status",
                        return_value=" M scripts/sympohy/runner.py\n",
                    ),
                    patch("scripts.sympohy.runner._pull_request_merged") as merged,
                    patch("scripts.sympohy.runner._finish_merged_issue") as finish,
                    patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                    patch("scripts.sympohy.runner.comment") as comment,
                ):
                    result = _resume_late_phase(
                        "#82",
                        issue,
                        self._config(root),
                        log_dir,
                        state,
                        previous_state={
                            "last_known_progress": {"total_logical_steps": 3}
                        },
                        resume_from=phase,
                    )

                final_state = json.loads(
                    (log_dir / "state.json").read_text(encoding="utf-8")
                )

            self.assertEqual(result, 2)
            merged.assert_not_called()
            finish.assert_not_called()
            set_issue_state.assert_called_once_with(
                "#82",
                current_labels=("sympohy:running", f"sympohy:phase:{phase}"),
                status="sympohy:blocked",
                phase=phase,
                cwd=worktree,
            )
            self.assertIn(
                f"{phase} phase worktree has uncommitted changes",
                comment.call_args.args[1],
            )
            self.assertEqual(final_state["status"], "blocked")

    def test_late_phase_resume_blocks_dirty_review_and_merge_worktrees(self) -> None:
        for phase in ("review", "finalize"):
            with self.subTest(phase=phase), TemporaryDirectory() as tmp:
                root = Path(tmp)
                worktree = root / "worktrees" / "issue-82"
                log_dir = root / "runs" / "issue-82"
                worktree.mkdir(parents=True)
                log_dir.mkdir(parents=True)
                issue = Issue(
                    number=82,
                    title="Dirty late phase",
                    body="",
                    labels=("sympohy:running", f"sympohy:phase:{phase}"),
                    comments=(),
                )
                state = _RunStateWriter(
                    issue_number=82,
                    log_dir=log_dir,
                    base_branch="main",
                    worktree=worktree,
                    branch="issue-82-sympohy",
                )

                with (
                    patch("scripts.sympohy.runner.ensure_worktree", return_value=worktree),
                    patch(
                        "scripts.sympohy.runner._current_branch",
                        return_value="issue-82-sympohy",
                    ),
                    patch(
                        "scripts.sympohy.runner._worktree_status",
                        return_value=" M scripts/sympohy/runner.py\n",
                    ),
                    patch("scripts.sympohy.runner._review_fix_loop") as review_fix_loop,
                    patch(
                        "scripts.sympohy.runner._run_final_verifier_and_merge"
                    ) as final_merge,
                    patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                    patch("scripts.sympohy.runner.comment") as comment,
                ):
                    result = _resume_late_phase(
                        "#82",
                        issue,
                        self._config(root),
                        log_dir,
                        state,
                        previous_state={"last_known_progress": {"review_round": 2}},
                        resume_from=phase,
                    )

                final_state = json.loads(
                    (log_dir / "state.json").read_text(encoding="utf-8")
                )

            self.assertEqual(result, 2)
            review_fix_loop.assert_not_called()
            final_merge.assert_not_called()
            set_issue_state.assert_called_once_with(
                "#82",
                current_labels=("sympohy:running", f"sympohy:phase:{phase}"),
                status="sympohy:blocked",
                phase=phase,
                cwd=worktree,
            )
            self.assertIn(
                f"{phase} phase worktree has uncommitted changes",
                comment.call_args.args[1],
            )
            self.assertEqual(final_state["status"], "blocked")

    def test_review_resume_blocks_empty_existing_pull_request_body(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / "worktrees" / "issue-82"
            log_dir = root / "runs" / "issue-82"
            worktree.mkdir(parents=True)
            log_dir.mkdir(parents=True)
            issue = Issue(
                number=82,
                title="Resume review with empty PR body",
                body="",
                labels=("sympohy:running", "sympohy:phase:review"),
                comments=(),
            )
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
                worktree=worktree,
                branch="issue-82-sympohy",
            )

            with (
                patch("scripts.sympohy.runner.ensure_worktree", return_value=worktree),
                patch(
                    "scripts.sympohy.runner._current_branch",
                    return_value="issue-82-sympohy",
                ),
                patch("scripts.sympohy.runner._worktree_status", return_value=""),
                patch(
                    "scripts.sympohy.runner._push_branch_and_ensure_draft_pull_request",
                    side_effect=_PullRequestMetadataError(
                        "existing pull request #91 body is empty; restore issue traceability, summary, and validation details before resuming"
                    ),
                ),
                patch("scripts.sympohy.runner._review_fix_loop") as review_fix_loop,
                patch(
                    "scripts.sympohy.runner._run_final_verifier_and_merge"
                ) as final_merge,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                result = _resume_late_phase(
                    "#82",
                    issue,
                    self._config(root),
                    log_dir,
                    state,
                    previous_state={"last_known_progress": {"review_round": 2}},
                    resume_from="review",
                )

            final_state = json.loads(
                (log_dir / "state.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result, 2)
        review_fix_loop.assert_not_called()
        final_merge.assert_not_called()
        set_issue_state.assert_any_call(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:review"),
            status="sympohy:running",
            phase="review",
            cwd=worktree,
        )
        set_issue_state.assert_any_call(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:review"),
            status="sympohy:blocked",
            phase="review",
            cwd=worktree,
        )
        self.assertIn("pull request safety check", comment.call_args.args[1])
        self.assertIn("existing pull request #91 body is empty", comment.call_args.args[1])
        self.assertEqual(final_state["status"], "blocked")
        self.assertEqual(
            final_state["last_known_progress"]["failed_command"],
            "pull request safety check",
        )

    def test_fix_resume_blocks_existing_fix_commit_with_dirty_worktree(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cwd = root / "worktrees" / "issue-82"
            log_dir = root / "runs" / "issue-82"
            cwd.mkdir(parents=True)
            log_dir.mkdir(parents=True)
            (log_dir / "review-2.json").write_text(
                json.dumps({"findings": [{"severity": "high", "summary": "fix"}]}),
                encoding="utf-8",
            )
            issue = Issue(
                number=82,
                title="Resume fix",
                body="",
                labels=("sympohy:running", "sympohy:phase:fix"),
                comments=(),
            )
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
                worktree=cwd,
                branch="issue-82-sympohy",
            )

            with (
                patch("scripts.sympohy.runner._commit_subject_exists", return_value=True),
                patch("scripts.sympohy.runner._commit_subjects", return_value=[]),
                patch("scripts.sympohy.runner._worktree_has_changes", return_value=True),
                patch(
                    "scripts.sympohy.runner._worktree_status",
                    return_value=" M scripts/sympohy/runner.py\n",
                ),
                patch("scripts.sympohy.runner._codex_text") as codex_text,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                result = _resume_fix_phase(
                    "#82",
                    issue,
                    self._config(root),
                    cwd,
                    log_dir,
                    state,
                    previous_state={"last_known_progress": {"review_round": 2}},
                )

            final_state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(result, 2)
        codex_text.assert_not_called()
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:fix"),
            status="sympohy:blocked",
            phase="fix",
            cwd=cwd,
        )
        self.assertIn("fix phase worktree has uncommitted changes", comment.call_args.args[1])
        self.assertEqual(final_state["status"], "blocked")

    def test_fix_resume_blocks_dirty_worktree_before_rerunning_codex(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            cwd = root / "worktrees" / "issue-82"
            log_dir = root / "runs" / "issue-82"
            cwd.mkdir(parents=True)
            log_dir.mkdir(parents=True)
            (log_dir / "review-2.json").write_text(
                json.dumps({"findings": [{"severity": "high", "summary": "fix"}]}),
                encoding="utf-8",
            )
            issue = Issue(
                number=82,
                title="Resume fix",
                body="",
                labels=("sympohy:running", "sympohy:phase:fix"),
                comments=(),
            )
            state = _RunStateWriter(
                issue_number=82,
                log_dir=log_dir,
                base_branch="main",
                worktree=cwd,
                branch="issue-82-sympohy",
            )

            with (
                patch(
                    "scripts.sympohy.runner._commit_subject_exists",
                    return_value=False,
                ) as commit_subject_exists,
                patch("scripts.sympohy.runner._commit_subjects", return_value=[]),
                patch("scripts.sympohy.runner._worktree_has_changes", return_value=True),
                patch(
                    "scripts.sympohy.runner._worktree_status",
                    return_value=" M scripts/sympohy/runner.py\n",
                ),
                patch("scripts.sympohy.runner._codex_text") as codex_text,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
                patch("scripts.sympohy.runner.comment") as comment,
            ):
                result = _resume_fix_phase(
                    "#82",
                    issue,
                    self._config(root),
                    cwd,
                    log_dir,
                    state,
                    previous_state={"last_known_progress": {"review_round": 2}},
                )

            final_state = json.loads((log_dir / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(result, 2)
        commit_subject_exists.assert_not_called()
        codex_text.assert_not_called()
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=("sympohy:running", "sympohy:phase:fix"),
            status="sympohy:blocked",
            phase="fix",
            cwd=cwd,
        )
        self.assertIn("fix phase worktree has uncommitted changes", comment.call_args.args[1])
        self.assertEqual(final_state["status"], "blocked")

    def test_issue_run_lock_takes_over_consistent_stale_heartbeat_with_live_pid(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-82"
            log_dir.mkdir(parents=True)
            stale = datetime.now(timezone.utc) - timedelta(minutes=31)
            lock_payload = {
                "issue": 82,
                "run_id": "old-run",
                "pid": os.getpid(),
                "heartbeat": stale.isoformat(),
            }
            state_payload = {
                "issue": 82,
                "run_id": "old-run",
                "phase": "implement",
                "status": "running",
                "pid": os.getpid(),
                "heartbeat": stale.isoformat(),
                "lock": {
                    "path": str(log_dir / "run.lock"),
                    "run_id": "old-run",
                },
            }
            (log_dir / "run.lock").write_text(
                json.dumps(lock_payload),
                encoding="utf-8",
            )
            (log_dir / "state.json").write_text(
                json.dumps(state_payload),
                encoding="utf-8",
            )

            lock = _IssueRunLock(
                issue_number=82,
                log_dir=log_dir,
                run_id="new-run",
                stale_status_after_minutes=30,
            )

            lock.acquire()
            lock.release()

            self.assertFalse((log_dir / "run.lock").exists())

    def test_issue_run_lock_refuses_fresh_heartbeat_with_live_pid(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-82"
            log_dir.mkdir(parents=True)
            fresh = datetime.now(timezone.utc)
            lock_payload = {
                "issue": 82,
                "run_id": "old-run",
                "pid": os.getpid(),
                "heartbeat": fresh.isoformat(),
            }
            state_payload = {
                "issue": 82,
                "run_id": "old-run",
                "phase": "implement",
                "status": "running",
                "pid": os.getpid(),
                "heartbeat": fresh.isoformat(),
                "lock": {
                    "path": str(log_dir / "run.lock"),
                    "run_id": "old-run",
                },
            }
            (log_dir / "run.lock").write_text(
                json.dumps(lock_payload),
                encoding="utf-8",
            )
            (log_dir / "state.json").write_text(
                json.dumps(state_payload),
                encoding="utf-8",
            )

            lock = _IssueRunLock(
                issue_number=82,
                log_dir=log_dir,
                run_id="new-run",
                stale_status_after_minutes=30,
            )

            with self.assertRaises(_RunLockedError):
                lock.acquire()

            payload = json.loads((log_dir / "run.lock").read_text(encoding="utf-8"))
            self.assertEqual(payload["run_id"], "old-run")

    def test_issue_run_lock_refuses_takeover_with_fresh_lock_heartbeat(self) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-82"
            log_dir.mkdir(parents=True)
            stale = datetime.now(timezone.utc) - timedelta(minutes=31)
            fresh = datetime.now(timezone.utc)
            lock_payload = {
                "issue": 82,
                "run_id": "old-run",
                "pid": os.getpid(),
                "heartbeat": fresh.isoformat(),
            }
            state_payload = {
                "issue": 82,
                "run_id": "old-run",
                "phase": "implement",
                "status": "running",
                "pid": os.getpid(),
                "heartbeat": stale.isoformat(),
                "lock": {
                    "path": str(log_dir / "run.lock"),
                    "run_id": "old-run",
                },
            }
            (log_dir / "run.lock").write_text(
                json.dumps(lock_payload),
                encoding="utf-8",
            )
            (log_dir / "state.json").write_text(
                json.dumps(state_payload),
                encoding="utf-8",
            )

            lock = _IssueRunLock(
                issue_number=82,
                log_dir=log_dir,
                run_id="new-run",
                stale_status_after_minutes=30,
            )

            with self.assertRaises(_RunLockedError):
                lock.acquire()

            payload = json.loads((log_dir / "run.lock").read_text(encoding="utf-8"))
            self.assertEqual(payload["run_id"], "old-run")

    def test_issue_run_lock_takes_over_consistent_stale_heartbeat_with_dead_pid(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-82"
            log_dir.mkdir(parents=True)
            stale = datetime.now(timezone.utc) - timedelta(minutes=31)
            lock_payload = {
                "issue": 82,
                "run_id": "old-run",
                "pid": 999999,
                "heartbeat": stale.isoformat(),
            }
            state_payload = {
                "issue": 82,
                "run_id": "old-run",
                "phase": "implement",
                "status": "running",
                "pid": 999999,
                "heartbeat": stale.isoformat(),
                "lock": {
                    "path": str(log_dir / "run.lock"),
                    "run_id": "old-run",
                },
            }
            (log_dir / "run.lock").write_text(
                json.dumps(lock_payload),
                encoding="utf-8",
            )
            (log_dir / "state.json").write_text(
                json.dumps(state_payload),
                encoding="utf-8",
            )

            lock = _IssueRunLock(
                issue_number=82,
                log_dir=log_dir,
                run_id="new-run",
                stale_status_after_minutes=30,
            )
            with patch("scripts.sympohy.runner.os.kill", side_effect=ProcessLookupError):
                lock.acquire()
                lock.release()

            self.assertFalse((log_dir / "run.lock").exists())

    def test_issue_run_lock_refuses_orphan_stale_lock_without_state(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-82"
            log_dir.mkdir(parents=True)
            stale = datetime.now(timezone.utc) - timedelta(minutes=31)
            (log_dir / "run.lock").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "run_id": "old-run",
                        "pid": 999999,
                        "heartbeat": stale.isoformat(),
                    }
                ),
                encoding="utf-8",
            )

            lock = _IssueRunLock(
                issue_number=82,
                log_dir=log_dir,
                run_id="new-run",
                stale_status_after_minutes=30,
            )
            with (
                patch("scripts.sympohy.runner.os.kill", side_effect=ProcessLookupError),
                self.assertRaises(_RunLockedError),
            ):
                lock.acquire()

            self.assertTrue((log_dir / "run.lock").exists())

    def test_issue_run_lock_refuses_stale_lock_with_corrupt_state(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-82"
            log_dir.mkdir(parents=True)
            stale = datetime.now(timezone.utc) - timedelta(minutes=31)
            (log_dir / "run.lock").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "run_id": "old-run",
                        "pid": 999999,
                        "heartbeat": stale.isoformat(),
                    }
                ),
                encoding="utf-8",
            )
            (log_dir / "state.json").write_text("{not json", encoding="utf-8")

            lock = _IssueRunLock(
                issue_number=82,
                log_dir=log_dir,
                run_id="new-run",
                stale_status_after_minutes=30,
            )
            with (
                patch("scripts.sympohy.runner.os.kill", side_effect=ProcessLookupError),
                self.assertRaises(_RunLockedError),
            ):
                lock.acquire()

            self.assertTrue((log_dir / "run.lock").exists())

    def test_issue_run_lock_refuses_takeover_when_guard_exists(self) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-82"
            log_dir.mkdir(parents=True)
            stale = datetime.now(timezone.utc) - timedelta(minutes=31)
            lock_payload = {
                "issue": 82,
                "run_id": "old-run",
                "pid": 999999,
                "heartbeat": stale.isoformat(),
            }
            state_payload = {
                "issue": 82,
                "run_id": "old-run",
                "phase": "implement",
                "status": "running",
                "pid": 999999,
                "heartbeat": stale.isoformat(),
                "lock": {
                    "path": str(log_dir / "run.lock"),
                    "run_id": "old-run",
                },
            }
            (log_dir / "run.lock").write_text(
                json.dumps(lock_payload),
                encoding="utf-8",
            )
            (log_dir / "state.json").write_text(
                json.dumps(state_payload),
                encoding="utf-8",
            )
            (log_dir / "run.lock.takeover").write_text("", encoding="utf-8")

            lock = _IssueRunLock(
                issue_number=82,
                log_dir=log_dir,
                run_id="new-run",
                stale_status_after_minutes=30,
            )

            with (
                patch("scripts.sympohy.runner.os.kill", side_effect=ProcessLookupError),
                self.assertRaises(_RunLockedError),
            ):
                lock.acquire()

            payload = json.loads((log_dir / "run.lock").read_text(encoding="utf-8"))
            self.assertEqual(payload["run_id"], "old-run")

    def test_issue_run_lock_refuses_mismatched_stale_lock(self) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-82"
            log_dir.mkdir(parents=True)
            stale = datetime.now(timezone.utc) - timedelta(minutes=31)
            (log_dir / "run.lock").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "run_id": "old-run",
                        "pid": 999999,
                        "heartbeat": stale.isoformat(),
                    }
                ),
                encoding="utf-8",
            )
            (log_dir / "state.json").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "run_id": "different-run",
                        "phase": "implement",
                        "status": "running",
                        "pid": 999999,
                        "heartbeat": stale.isoformat(),
                    }
                ),
                encoding="utf-8",
            )

            lock = _IssueRunLock(
                issue_number=82,
                log_dir=log_dir,
                run_id="new-run",
                stale_status_after_minutes=30,
            )

            with (
                patch("scripts.sympohy.runner.os.kill", side_effect=ProcessLookupError),
                self.assertRaises(_RunLockedError),
            ):
                lock.acquire()

            self.assertTrue((log_dir / "run.lock").exists())

    def test_issue_run_lock_refuses_mismatched_fresh_lock(self) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-82"
            log_dir.mkdir(parents=True)
            fresh = datetime.now(timezone.utc)
            (log_dir / "run.lock").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "run_id": "old-run",
                        "pid": 999999,
                        "heartbeat": fresh.isoformat(),
                    }
                ),
                encoding="utf-8",
            )
            (log_dir / "state.json").write_text(
                json.dumps(
                    {
                        "issue": 82,
                        "run_id": "different-run",
                        "phase": "implement",
                        "status": "running",
                        "pid": 999999,
                        "heartbeat": fresh.isoformat(),
                    }
                ),
                encoding="utf-8",
            )

            lock = _IssueRunLock(
                issue_number=82,
                log_dir=log_dir,
                run_id="new-run",
                stale_status_after_minutes=30,
            )

            with (
                patch("scripts.sympohy.runner.os.kill", side_effect=ProcessLookupError),
                self.assertRaises(_RunLockedError),
            ):
                lock.acquire()

            payload = json.loads((log_dir / "run.lock").read_text(encoding="utf-8"))
            self.assertEqual(payload["run_id"], "old-run")

    def _config(self, root: Path) -> SympohyConfig:
        return SympohyConfig(
            max_workers=10,
            base_branch="main",
            worktree_root=root / "worktrees",
            run_log_root=root / "runs",
            stale_status_after_minutes=30,
            hooks=("task ci",),
            review_max_rounds=5,
            retry_max_attempts=3,
            final_verifier_fix_max_attempts=2,
            stage_gate_command=None,
        )


if __name__ == "__main__":
    unittest.main()
