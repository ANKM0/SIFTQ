from __future__ import annotations

from pathlib import Path
import unittest

from scripts.sympohy.stage_gate import evaluate_stage


class SympohyStageGateTest(unittest.TestCase):
    def test_request_elaboration_requires_ac_and_dod(self) -> None:
        result = evaluate_stage(
            "request-elaboration",
            issue_number=101,
            run_dir=Path(".sympohy/runs/issue-101"),
            context={
                "acceptance_criteria": ["AC exists"],
                "definition_of_done": ["DoD exists"],
            },
        )

        self.assertEqual(result["status"], "pass")

    def test_artifact_stage_accepts_not_needed_with_reason(self) -> None:
        result = evaluate_stage(
            "wireframes",
            issue_number=101,
            run_dir=Path(".sympohy/runs/issue-101"),
            context={
                "artifact_decisions": {
                    "wireframes": {
                        "mode": "not_needed",
                        "reason": "No UI change.",
                    }
                }
            },
        )

        self.assertEqual(result["status"], "pass")

    def test_artifact_stage_retries_missing_evidence(self) -> None:
        result = evaluate_stage(
            "requirements",
            issue_number=101,
            run_dir=Path(".sympohy/runs/issue-101"),
            context={"artifact_decisions": {"requirements": {"mode": "new"}}},
        )

        self.assertEqual(result["status"], "retry")
        self.assertEqual(result["return_to"], "requirements")

    def test_artifact_stage_retries_when_evidence_path_does_not_exist(self) -> None:
        result = evaluate_stage(
            "design",
            issue_number=101,
            run_dir=Path(".sympohy/runs/issue-101"),
            context={
                "workspace": "/tmp",
                "artifact_decisions": {
                    "design": {
                        "mode": "existing",
                        "path": "docs/design/missing.md",
                    }
                },
            },
        )

        self.assertEqual(result["status"], "retry")
        self.assertIn("does not exist", str(result["reason"]))

    def test_merge_gate_retries_to_implementation_when_evidence_is_missing(self) -> None:
        result = evaluate_stage(
            "merge",
            issue_number=101,
            run_dir=Path(".sympohy/runs/issue-101"),
            context={
                "acceptance_criteria_satisfied": True,
                "definition_of_done_satisfied": True,
                "ci_passed": False,
                "review_approved": True,
            },
        )

        self.assertEqual(result["status"], "retry")
        self.assertEqual(result["return_to"], "implementation")


if __name__ == "__main__":
    unittest.main()
