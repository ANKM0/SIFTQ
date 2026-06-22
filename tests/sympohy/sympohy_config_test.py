from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.sympohy.config import CodexModelConfig, default_config, load_config


class SympohyConfigTest(unittest.TestCase):
    def test_default_config_sets_stage_gate_and_retry_limits(self) -> None:
        config = default_config()

        self.assertEqual(config.review_max_rounds, 10)
        self.assertEqual(config.ci_retry_max_attempts, 50)
        self.assertEqual(config.watch_poll_interval_seconds, 60)
        self.assertEqual(config.final_verifier_fix_max_attempts, 2)
        self.assertEqual(config.stage_gate_command, "task ai:sympohy:stage-gate")
        self.assertEqual(
            config.codex_model_for("implementation"),
            CodexModelConfig("gpt-5.5", "high"),
        )
        self.assertEqual(
            config.codex_model_for("review"),
            CodexModelConfig("gpt-5.5", "xhigh"),
        )

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
watch_poll_interval_seconds: 30
review_max_rounds: 7
ci_retry_max_attempts: 40
final_verifier_fix_max_attempts: 5
stage_gate_command: task ai:sympohy:stage-gate
codex_model_triage: gpt-5.4-mini
codex_reasoning_triage: medium
codex_model_review: gpt-5.5
codex_reasoning_review: xhigh
hooks:
  - task test
  - task lint
""",
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config.ci_retry_max_attempts, 40)
        self.assertEqual(config.watch_poll_interval_seconds, 30)
        self.assertEqual(config.final_verifier_fix_max_attempts, 5)
        self.assertEqual(config.stage_gate_command, "task ai:sympohy:stage-gate")
        self.assertEqual(config.hooks, ("task test", "task lint"))
        self.assertEqual(
            config.codex_model_for("triage"),
            CodexModelConfig("gpt-5.4-mini", "medium"),
        )
        self.assertEqual(
            config.codex_model_for("review"),
            CodexModelConfig("gpt-5.5", "xhigh"),
        )

    def test_load_config_rejects_negative_final_verifier_fix_limit(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text(
                "final_verifier_fix_max_attempts: -1\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "final_verifier_fix_max_attempts must be non-negative",
            ):
                load_config(config_path)

    def test_load_config_rejects_unknown_codex_model_role(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text(
                "codex_model_unknown: gpt-5.5\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "unsupported codex model role: unknown",
            ):
                load_config(config_path)


if __name__ == "__main__":
    unittest.main()
