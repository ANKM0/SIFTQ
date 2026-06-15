from __future__ import annotations

import json
import unittest

from scripts.sympohy import (
    extract_acceptance_set,
    is_candidate_issue,
    merge_gate_allows_merge,
    next_retry_action,
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
        self.assertFalse(
            is_candidate_issue(
                {"state": "OPEN", "labels": [{"name": "sympohy:running"}]}
            )
        )

    def test_running_issue_with_phase_is_currently_not_candidate(self) -> None:
        issue = {
            "state": "OPEN",
            "labels": [
                {"name": "enhancement"},
                {"name": "sympohy:running"},
                {"name": "sympohy:phase:implement"},
            ],
        }

        self.assertFalse(is_candidate_issue(issue))

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


if __name__ == "__main__":
    unittest.main()
