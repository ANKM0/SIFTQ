from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.sympohy.config import SympohyConfig
from scripts.sympohy.github import Issue
from scripts.sympohy.runner import (
    _IssueRunLock,
    _AmbiguousPullRequestError,
    _RunLockedError,
    _RunStateWriter,
    _UnsafeRecoveryError,
    _commit_all_if_new,
    _ensure_draft_pull_request,
    _infer_implementation_recovery,
    _pull_request_exists,
    _resume_fix_phase,
    _run_final_verifier_and_merge,
    _run_hooks,
    ensure_worktree,
    resume_issue,
    run_issue,
    watch,
)


class SympohyRunnerTest(unittest.TestCase):
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
                popen.return_value.poll.return_value = None

                result = watch(config)

        self.assertEqual(result, 0)
        set_issue_state.assert_called_once_with(
            "#82",
            current_labels=["enhancement"],
            status="sympohy:pending",
            phase="triage",
        )
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
                popen.return_value.poll.return_value = None

                result = watch(config)

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
                popen.return_value.poll.return_value = None

                result = watch(config)

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
                popen.return_value.poll.return_value = None

                result = watch(config)

        self.assertEqual(result, 0)
        set_issue_state.assert_not_called()
        command = popen.call_args.args[0]
        self.assertEqual(command[-2:], ["resume", "#82"])

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
                popen.return_value.poll.return_value = None

                result = watch(config)

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

    def test_resume_issue_selects_recovery_mode_from_phase_label(self) -> None:
        for phase in ("triage", "implement", "hooks", "review", "fix", "merge"):
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
                            "phase": phase,
                            "status": "running",
                            "pid": os.getpid(),
                            "heartbeat": stale_heartbeat.isoformat(),
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
                        "phase": "hooks",
                        "status": "running",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
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
                "phase": "implement",
                "status": "running",
                "pid": os.getpid(),
                "heartbeat": datetime.now(timezone.utc).isoformat(),
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
                        "phase": "triage",
                        "status": "running",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
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
                patch(
                    "scripts.sympohy.runner._codex_json",
                    return_value={"logical_steps": [{"name": "one"}]},
                ),
                patch("scripts.sympohy.runner._codex_text", return_value=""),
                patch("scripts.sympohy.runner._run_hooks", return_value=1),
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
                        "phase": "triage",
                        "status": "running",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
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
                        "phase": "implement",
                        "status": "running",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
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
                if args == ["git", "branch", "--show-current"]:
                    return "issue-82-sympohy\n"
                raise AssertionError(f"unexpected check_output: {args}")

            def codex_json(
                _prompts: list[str],
                *,
                log_path: Path,
                **_kwargs: object,
            ) -> dict[str, object]:
                if log_path.name == "final-verifier.json":
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
                        "phase": "implement",
                        "status": "running",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
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
                if args == ["git", "branch", "--show-current"]:
                    return "issue-82-sympohy\n"
                raise AssertionError(f"unexpected check_output: {args}")

            def codex_json(
                _prompts: list[str],
                *,
                log_path: Path,
                **_kwargs: object,
            ) -> dict[str, object]:
                if log_path.name == "final-verifier.json":
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
                        "phase": "implement",
                        "status": "running",
                        "pid": os.getpid(),
                        "heartbeat": stale_heartbeat.isoformat(),
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
                if args == ["git", "branch", "--show-current"]:
                    return "issue-82-sympohy\n"
                raise AssertionError(f"unexpected check_output: {args}")

            def codex_json(
                _prompts: list[str],
                *,
                log_path: Path,
                **_kwargs: object,
            ) -> dict[str, object]:
                if log_path.name == "final-verifier.json":
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
        self.assertIn(["gh", "pr", "create", "--draft", "--fill"], heartbeat_commands)
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
                labels=("sympohy:done", "sympohy:phase:merge"),
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
        self.assertEqual(state["phase"], "merge")
        self.assertEqual(state["status"], "done")
        self.assertEqual(state["last_known_progress"]["resume_point"], "completed")

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

    def test_ensure_draft_pull_request_skips_existing_pr(self) -> None:
        with (
            patch(
                "scripts.sympohy.runner._current_branch",
                return_value="issue-82-sympohy",
            ),
            patch("scripts.sympohy.runner._pull_request_exists", return_value=True),
            patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
        ):
            _ensure_draft_pull_request(cwd=Path("/tmp/worktree"))

        check_call.assert_not_called()

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
                labels=("sympohy:running", "sympohy:phase:merge"),
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
                ),
                patch(
                    "scripts.sympohy.runner._run_command_with_heartbeat",
                    return_value=0,
                ) as run_command,
                patch("scripts.sympohy.runner._pull_request_merged", return_value=False),
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
                patch("scripts.sympohy.runner.set_issue_state"),
            ):
                result = _run_final_verifier_and_merge(
                    "#82",
                    issue,
                    worktree,
                    log_dir,
                    state,
                    total_steps=3,
                )

        self.assertEqual(result, 0)
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
                labels=("sympohy:running", "sympohy:phase:merge"),
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
                patch("scripts.sympohy.runner._codex_json") as codex_json,
                patch("scripts.sympohy.runner.subprocess.check_call") as check_call,
                patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
            ):
                result = _run_final_verifier_and_merge(
                    "#82",
                    issue,
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
            current_labels=("sympohy:running", "sympohy:phase:merge"),
            status="sympohy:done",
            phase="merge",
        )
        self.assertEqual(final_state["status"], "done")
        self.assertEqual(
            final_state["last_known_progress"]["message"],
            "reconciled already-merged pull request",
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

    def test_issue_run_lock_takes_over_orphan_stale_lock_without_state(
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
            with patch("scripts.sympohy.runner.os.kill", side_effect=ProcessLookupError):
                lock.acquire()
                lock.release()

            self.assertFalse((log_dir / "run.lock").exists())

    def test_issue_run_lock_takes_over_stale_lock_with_corrupt_state(
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
            with patch("scripts.sympohy.runner.os.kill", side_effect=ProcessLookupError):
                lock.acquire()
                lock.release()

            self.assertFalse((log_dir / "run.lock").exists())

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

            with self.assertRaises(_RunLockedError):
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
        )


if __name__ == "__main__":
    unittest.main()
