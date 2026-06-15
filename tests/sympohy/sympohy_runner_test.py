from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.sympohy.runner import _RunStateWriter


class SympohyRunnerTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
