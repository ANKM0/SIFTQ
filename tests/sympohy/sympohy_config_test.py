from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.sympohy.config import default_config, load_config


class SympohyConfigTest(unittest.TestCase):
    def test_default_config_sets_final_verifier_fix_limit(self) -> None:
        config = default_config()

        self.assertEqual(config.final_verifier_fix_max_attempts, 2)

    def test_load_config_reads_final_verifier_fix_limit(self) -> None:
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
retry_max_attempts: 4
final_verifier_fix_max_attempts: 5
hooks:
  - task test
  - task lint
""",
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config.final_verifier_fix_max_attempts, 5)
        self.assertEqual(config.hooks, ("task test", "task lint"))


if __name__ == "__main__":
    unittest.main()
