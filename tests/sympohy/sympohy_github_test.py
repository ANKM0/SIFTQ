from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.sympohy.github import comment, set_issue_state


class SympohyGithubTest(unittest.TestCase):
    def test_set_issue_state_rechecks_labels_and_skips_duplicate_transition(self) -> None:
        with (
            patch(
                "scripts.sympohy.github.gh_json",
                return_value={
                    "labels": [
                        {"name": "sympohy:blocked"},
                        {"name": "sympohy:phase:implement"},
                    ]
                },
            ) as gh_json,
            patch("scripts.sympohy.github.gh_run") as gh_run,
        ):
            set_issue_state(
                "#82",
                current_labels=("sympohy:running", "sympohy:phase:implement"),
                status="sympohy:blocked",
                phase="implement",
            )

        gh_json.assert_called_once_with(
            ["issue", "view", "#82", "--json", "labels"],
            cwd=None,
        )
        gh_run.assert_not_called()

    def test_comment_skips_existing_body(self) -> None:
        body = "sympohy blocked this run."
        with (
            patch(
                "scripts.sympohy.github.gh_json",
                return_value={"comments": [{"body": body}]},
            ) as gh_json,
            patch("scripts.sympohy.github.gh_run") as gh_run,
        ):
            comment("#82", body)

        gh_json.assert_called_once_with(
            ["issue", "view", "#82", "--json", "comments"],
            cwd=None,
        )
        gh_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
