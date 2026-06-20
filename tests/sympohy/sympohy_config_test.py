from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.sympohy.config import default_config, load_config


class SympohyConfigTest(unittest.TestCase):
    def test_default_config_sets_stage_gate_and_retry_limits(self) -> None:
        config = default_config()

        self.assertEqual(config.review_max_rounds, 10)
        self.assertEqual(config.ci_retry_max_attempts, 50)
        self.assertIsNone(config.merge_gate_retry_max_attempts)
        self.assertEqual(config.stage_gate_command, "task ai:sympohy:stage-gate")

    def test_load_config_reads_stage_gate_and_retry_limits(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text(
                """
max_workers: 4
base_branch: develop
worktree_root: .tmp/worktrees
run_log_root: .tmp/runs
stale_status_after_minutes: 15
review_max_rounds: 7
ci_retry_max_attempts: 40
merge_gate_retry_max_attempts: 5
stage_gate_command: task ai:sympohy:stage-gate
hooks:
  - task test
  - task lint
""",
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config.ci_retry_max_attempts, 40)
        self.assertEqual(config.merge_gate_retry_max_attempts, 5)
        self.assertEqual(config.stage_gate_command, "task ai:sympohy:stage-gate")
        self.assertEqual(config.hooks, ("task test", "task lint"))

    def test_load_config_rejects_negative_merge_gate_retry_limit(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text(
                "merge_gate_retry_max_attempts: -1\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "merge_gate_retry_max_attempts must be non-negative",
            ):
                load_config(config_path)


if __name__ == "__main__":
    unittest.main()
