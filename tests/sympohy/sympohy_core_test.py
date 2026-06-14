from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.sympohy import (
    extract_acceptance_set,
    is_candidate_issue,
    merge_gate_allows_merge,
    next_retry_action,
    transition_labels,
    validate_commit_subject,
)
from scripts.sympohy.config import SympohyConfig
from scripts.sympohy.core import parse_review_json
from scripts.sympohy.runner import _logical_steps, watch
from scripts.sympohy.systemd import _systemd_escape


class FakeProcess:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.wait_called = False

    def wait(self) -> int:
        self.wait_called = True
        return self.returncode


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

    def test_extracts_ac_dod_after_fenced_markdown_templates(self) -> None:
        body = """
## Requirements template

```md
## Acceptance Criteria

## Open Questions
```

## AC

- [ ] real AC

## DoD

- [ ] real DoD
"""

        result = extract_acceptance_set(body, [])

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.acceptance_criteria, ("real AC",))
        self.assertEqual(result.definition_of_done, ("real DoD",))

    def test_open_issue_without_sympohy_status_is_candidate(self) -> None:
        issue = {"state": "OPEN", "labels": [{"name": "bug"}]}

        self.assertTrue(is_candidate_issue(issue))
        self.assertFalse(
            is_candidate_issue(
                {"state": "OPEN", "labels": [{"name": "sympohy:running"}]}
            )
        )

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

    def test_systemd_path_escape_preserves_executable_lookup(self) -> None:
        self.assertEqual(
            _systemd_escape('/opt/tools:/tmp/has"quote:/tmp/has%percent'),
            '/opt/tools:/tmp/has\\"quote:/tmp/has%%percent',
        )

    def test_watch_waits_for_spawned_workers_under_systemd(self) -> None:
        process = FakeProcess()
        config = SympohyConfig(
            max_workers=10,
            base_branch="main",
            worktree_root=Path(".sympohy/worktrees"),
            run_log_root=Path(".sympohy/runs"),
            hooks=("task ci",),
            review_max_rounds=5,
            retry_max_attempts=3,
        )

        with (
            patch(
                "scripts.sympohy.runner.list_candidate_issues",
                return_value=[{"number": 79, "labels": []}],
            ),
            patch("scripts.sympohy.runner.set_issue_state") as set_issue_state,
            patch("scripts.sympohy.runner.subprocess.Popen", return_value=process),
        ):
            result = watch(config)

        self.assertEqual(result, 0)
        self.assertTrue(process.wait_called)
        set_issue_state.assert_called_once_with(
            "#79",
            current_labels=[],
            status="sympohy:pending",
            phase="triage",
        )

    def test_logical_steps_accepts_string_and_object_planner_output(self) -> None:
        self.assertEqual(
            _logical_steps({"logical_steps": ["write docs", {"description": "run tests"}]}),
            [{"description": "write docs"}, {"description": "run tests"}],
        )


if __name__ == "__main__":
    unittest.main()
