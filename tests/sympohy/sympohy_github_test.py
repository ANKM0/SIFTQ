from __future__ import annotations

import unittest
from unittest.mock import call, patch

from scripts.sympohy.github import (
    list_legacy_task_issues,
    migrate_issue_labels,
    migrate_legacy_tasks,
    comment,
    fetch_issue,
    set_issue_state,
    sync_labels,
)


class SympohyGithubTest(unittest.TestCase):
    def test_fetch_issue_reads_state_reason(self) -> None:
        with patch(
            "scripts.sympohy.github.gh_json",
            return_value={
                "number": 82,
                "title": "Implement feature",
                "body": "",
                "state": "CLOSED",
                "stateReason": "COMPLETED",
                "labels": [{"name": "sympohy:done"}],
                "comments": [],
            },
        ) as gh_json:
            issue = fetch_issue("#82")

        gh_json.assert_called_once_with(
            [
                "issue",
                "view",
                "#82",
                "--json",
                "number,title,body,labels,comments,state,stateReason",
            ],
            cwd=None,
        )
        self.assertEqual(issue.state, "CLOSED")
        self.assertEqual(issue.state_reason, "COMPLETED")

    def test_set_issue_state_refreshes_cached_labels_for_noop_transition(self) -> None:
        with (
            patch(
                "scripts.sympohy.github.gh_json",
                return_value={
                    "labels": [
                        {"name": "sympohy:running"},
                        {"name": "sympohy:phase:implement"},
                    ]
                },
            ) as gh_json,
            patch("scripts.sympohy.github.gh_run") as gh_run,
        ):
            set_issue_state(
                "#82",
                current_labels=("sympohy:running", "sympohy:phase:implement"),
                status="sympohy:running",
                phase="implement",
            )

        gh_json.assert_called_once_with(["issue", "view", "#82", "--json", "labels"], cwd=None)
        gh_run.assert_not_called()

    def test_set_issue_state_refreshes_stale_cached_labels(self) -> None:
        with (
            patch(
                "scripts.sympohy.github.gh_json",
                return_value={
                    "labels": [
                        {"name": "sympohy:running"},
                        {"name": "sympohy:blocked"},
                        {"name": "sympohy:phase:finalize"},
                    ]
                },
            ) as gh_json,
            patch("scripts.sympohy.github.gh_run") as gh_run,
        ):
            set_issue_state(
                "#82",
                current_labels=("sympohy:running", "sympohy:phase:finalize"),
                status="sympohy:running",
                phase="implement",
        )

        gh_json.assert_called_once_with(["issue", "view", "#82", "--json", "labels"], cwd=None)
        gh_run.assert_has_calls(
            [
                call(["issue", "edit", "#82", "--remove-label", "sympohy:blocked,sympohy:phase:finalize"], cwd=None),
                call(["issue", "edit", "#82", "--add-label", "sympohy:phase:implement"], cwd=None),
            ],
            any_order=False,
        )

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

    def test_sync_labels_migrates_issues_before_deleting_legacy_task_labels(self) -> None:
        events: list[str] = []

        def run(args: list[str], *, cwd=None) -> None:  # noqa: ANN001
            if args[:2] == ["label", "delete"]:
                events.append(f"delete:{args[2]}")

        with (
            patch(
                "scripts.sympohy.github.gh_json",
                return_value=[
                    {"name": "ai:impl-ready"},
                    {"name": "bug"},
                    {"name": "takt:running"},
                    {"name": "taqt:blocked"},
                ],
            ),
            patch("scripts.sympohy.github.gh_run", side_effect=run),
            patch("scripts.sympohy.github.migrate_legacy_tasks") as migrate,
        ):
            migrate.side_effect = lambda *, cwd=None: events.append("migrate")

            sync_labels()

        self.assertEqual(
            events,
            [
                "migrate",
                "delete:ai:impl-ready",
                "delete:takt:running",
                "delete:taqt:blocked",
            ],
        )
        self.assertEqual(migrate.call_count, 1)

    def test_sync_labels_aborts_when_legacy_migration_is_incomplete(self) -> None:
        issue = {
            "number": 82,
            "title": "incomplete",
            "state": "OPEN",
            "labels": [{"name": "taqt:running"}],
        }

        with (
            patch(
                "scripts.sympohy.github.gh_json",
                return_value=[
                    {"name": "sympohy:pending"},
                    {"name": "taqt:running"},
                ],
            ),
            patch(
                "scripts.sympohy.github.list_legacy_task_issues",
                side_effect=[[issue], [issue]],
            ),
            patch("scripts.sympohy.github.migrate_legacy_tasks") as migrate,
            patch("scripts.sympohy.github.gh_run") as gh_run,
        ):
            migrate.return_value = None
            with self.assertRaises(RuntimeError) as context:
                sync_labels()

        self.assertIn("legacy migration incomplete", str(context.exception))
        self.assertEqual(migrate.call_count, 1)
        gh_run.assert_not_called()

    def test_migrate_issue_labels_replaces_only_managed_labels(self) -> None:
        with (
            patch(
                "scripts.sympohy.github.gh_json",
                return_value={
                    "number": 82,
                    "title": "Implement feature",
                    "body": "## AC\n- [ ] AC\n\n## DoD\n- [ ] DoD",
                    "state": "OPEN",
                    "labels": [
                        {"name": "bug"},
                        {"name": "ai:review"},
                    ],
                    "comments": [{"body": "related to #12"}],
                    "assignees": [{"login": "octo"}],
                    "milestone": {"number": 1},
                },
            ),
            patch("scripts.sympohy.github.gh_run") as gh_run,
        ):
            result = migrate_issue_labels("#82")

        self.assertTrue(result["changed"])
        self.assertEqual(
            result["labels"],
            ["bug", "sympohy:phase:review", "sympohy:running"],
        )
        self.assertEqual(
            gh_run.call_args_list[0].args[0],
            [
                "issue",
                "edit",
                "#82",
                "--remove-label",
                "ai:review",
            ],
        )
        self.assertEqual(
            gh_run.call_args_list[1].args[0],
            [
                "issue",
                "edit",
                "#82",
                "--add-label",
                "sympohy:phase:review,sympohy:running",
            ],
        )

    def test_migrate_issue_labels_dry_run_does_not_write(self) -> None:
        with (
            patch(
                "scripts.sympohy.github.gh_json",
                return_value={
                    "number": 82,
                    "title": "Implement feature",
                    "body": "",
                    "state": "OPEN",
                    "labels": [{"name": "ai:impl-ready"}],
                    "comments": [],
                },
            ),
            patch("scripts.sympohy.github.gh_run") as gh_run,
        ):
            result = migrate_issue_labels("#82", dry_run=True)

        self.assertTrue(result["dry_run"])
        self.assertTrue(result["changed"])
        gh_run.assert_not_called()

    def test_list_legacy_task_issues_filters_to_legacy_task_labels(self) -> None:
        with patch(
            "scripts.sympohy.github.gh_json",
            return_value=[
                {
                    "number": 81,
                    "title": "legacy",
                    "state": "OPEN",
                    "labels": [{"name": "ai:impl-ready"}],
                },
                {
                    "number": 82,
                    "title": "plain",
                    "state": "OPEN",
                    "labels": [{"name": "bug"}],
                },
            ],
        ):
            issues = list_legacy_task_issues()

        self.assertEqual([issue["number"] for issue in issues], [81])

    def test_migrate_legacy_tasks_can_target_one_issue(self) -> None:
        with patch("scripts.sympohy.github.migrate_issue_labels") as migrate_issue:
            migrate_issue.return_value = {"issue": 82}

            result = migrate_legacy_tasks("#82", dry_run=True)

        self.assertEqual(result, [{"issue": 82}])
        migrate_issue.assert_called_once_with("#82", dry_run=True, cwd=None)


if __name__ == "__main__":
    unittest.main()
