from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.sympohy.config import SympohyConfig
from scripts.sympohy.github import Issue
from scripts.sympohy.runner import (
    _RunStateWriter,
    _infer_implementation_recovery,
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

    def test_resume_issue_records_stale_reason_before_restarting_run(self) -> None:
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
            ):
                result = resume_issue("#82", config)

            state = json.loads(
                (config.run_log_root / "issue-82" / "state.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result, 0)
        run_issue.assert_called_once_with("#82", config, recover=True)
        self.assertEqual(state["phase"], "implement")
        self.assertEqual(state["last_known_progress"]["resume_point"], "implement")
        self.assertEqual(state["last_known_progress"]["stale_reason"], "missing state")

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
                patch("scripts.sympohy.runner.subprocess.check_call"),
            ):
                result = run_issue("#82", config, recover=True)

        self.assertEqual(result, 0)
        codex_text.assert_called_once()
        prompts = codex_text.call_args.args[0]
        self.assertIn("Implement logical step 3", prompts[0])

    def test_implementation_recovery_reuses_dirty_worktree_for_next_step(self) -> None:
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
        self.assertEqual(recovery.worktree_logical_step, 2)
        self.assertTrue(recovery.should_reuse_worktree(2))

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
        self.assertEqual(state["phase"], "implement")
        self.assertEqual(state["status"], "running")
        self.assertEqual(state["pid"], os.getpid())
        self.assertEqual(state["heartbeat"], "2026-06-15T12:00:00Z")
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

    def _config(self, root: Path) -> SympohyConfig:
        return SympohyConfig(
            max_workers=10,
            base_branch="main",
            worktree_root=root / "worktrees",
            run_log_root=root / "runs",
            hooks=("task ci",),
            review_max_rounds=5,
            retry_max_attempts=3,
        )


if __name__ == "__main__":
    unittest.main()
