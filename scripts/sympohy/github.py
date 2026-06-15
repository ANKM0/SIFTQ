from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .core import (
    DEFAULT_STALE_STATUS_AFTER_MINUTES,
    LEGACY_TASK_LABEL_PREFIXES,
    PHASE_LABELS,
    STATUS_LABELS,
    is_candidate_issue,
    migrate_task_labels,
    transition_labels,
)


REQUIRED_LABELS = {
    "sympohy:pending": "Queued for sympohy execution.",
    "sympohy:running": "Currently being processed by sympohy.",
    "sympohy:blocked": "Blocked by missing input or repeated automation failure.",
    "sympohy:done": "Completed and merged by sympohy.",
    "sympohy:phase:triage": "Sympohy is checking AC/DoD and prerequisites.",
    "sympohy:phase:implement": "Sympohy is implementing planned changes.",
    "sympohy:phase:hooks": "Sympohy is running verification hooks.",
    "sympohy:phase:review": "Sympohy is running adversarial review.",
    "sympohy:phase:fix": "Sympohy is fixing review or hook findings.",
    "sympohy:phase:merge": "Sympohy is verifying and merging the PR.",
}


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str
    labels: tuple[str, ...]
    comments: tuple[Mapping[str, object], ...]
    state: str = "UNKNOWN"


def gh_json(args: Sequence[str], *, cwd: Path | None = None) -> object:
    output = subprocess.check_output(["gh", *args], cwd=cwd, text=True)
    return json.loads(output)


def gh_run(args: Sequence[str], *, cwd: Path | None = None) -> None:
    subprocess.check_call(["gh", *args], cwd=cwd)


def fetch_issue(issue_ref: str, *, cwd: Path | None = None) -> Issue:
    payload = gh_json(
        [
            "issue",
            "view",
            issue_ref,
            "--json",
            "number,title,body,labels,comments,state",
        ],
        cwd=cwd,
    )
    if not isinstance(payload, Mapping):
        raise ValueError("gh issue view returned non-object JSON")
    return Issue(
        number=int(payload["number"]),
        title=str(payload.get("title", "")),
        body=str(payload.get("body", "")),
        labels=tuple(_label_names(payload.get("labels", []))),
        comments=tuple(_comments(payload.get("comments", []))),
        state=str(payload.get("state", "UNKNOWN")),
    )


def list_candidate_issues(
    *,
    limit: int,
    run_log_root: Path = Path(".sympohy/runs"),
    stale_status_after_minutes: int = DEFAULT_STALE_STATUS_AFTER_MINUTES,
    cwd: Path | None = None,
) -> list[Mapping[str, object]]:
    payload = gh_json(
        [
            "issue",
            "list",
            "--state",
            "open",
            "--limit",
            str(limit),
            "--json",
            "number,title,state,labels",
        ],
        cwd=cwd,
    )
    if not isinstance(payload, list):
        raise ValueError("gh issue list returned non-list JSON")
    return [
        issue
        for issue in payload
        if isinstance(issue, Mapping)
        and is_candidate_issue(
            issue,
            run_log_root=run_log_root,
            stale_status_after_minutes=stale_status_after_minutes,
        )
    ]


def sync_labels(*, cwd: Path | None = None) -> None:
    legacy_issues = list_legacy_task_issues(cwd=cwd)
    if legacy_issues:
        _validate_legacy_migration_plan(legacy_issues)

    migrate_legacy_tasks(cwd=cwd)

    if legacy_issues:
        remaining = list_legacy_task_issues(cwd=cwd)
        if remaining:
            remaining_numbers = [
                int(issue["number"])
                for issue in remaining
                if isinstance(issue.get("number"), int)
                or (isinstance(issue.get("number"), str) and issue["number"].isdigit())
            ]
            raise RuntimeError(
                "legacy migration incomplete; rerun task ai:sympohy:migrate -- --all "
                f"first: issues {remaining_numbers[:10]}"
            )

    payload = gh_json(["label", "list", "--limit", "500", "--json", "name"], cwd=cwd)
    if not isinstance(payload, list):
        raise ValueError("gh label list returned non-list JSON")
    existing = set(_label_names(payload))

    for name, description in REQUIRED_LABELS.items():
        if name in existing:
            gh_run(["label", "edit", name, "--description", description], cwd=cwd)
        else:
            gh_run(["label", "create", name, "--description", description], cwd=cwd)

    for name in sorted(existing):
        if _is_legacy_task_label(name):
            gh_run(["label", "delete", name, "--yes"], cwd=cwd)


def list_legacy_task_issues(
    *,
    limit: int = 500,
    cwd: Path | None = None,
) -> list[Mapping[str, object]]:
    payload = gh_json(
        [
            "issue",
            "list",
            "--state",
            "all",
            "--limit",
            str(limit),
            "--json",
            "number,title,state,labels,assignees,milestone",
        ],
        cwd=cwd,
    )
    if not isinstance(payload, list):
        raise ValueError("gh issue list returned non-list JSON")
    return [
        issue
        for issue in payload
        if isinstance(issue, Mapping)
        and _has_legacy_task_label(_label_names(issue.get("labels", [])))
    ]


def migrate_issue_labels(
    issue_ref: str,
    *,
    dry_run: bool = False,
    cwd: Path | None = None,
) -> Mapping[str, object]:
    issue = fetch_issue(issue_ref, cwd=cwd)
    desired = migrate_task_labels(issue.labels, issue_state=issue.state)
    remove, add = _migration_label_diff(issue.labels, desired)
    if not dry_run:
        if remove:
            gh_run(
                ["issue", "edit", issue_ref, "--remove-label", ",".join(sorted(remove))],
                cwd=cwd,
            )
        if add:
            gh_run(
                ["issue", "edit", issue_ref, "--add-label", ",".join(sorted(add))],
                cwd=cwd,
            )
    return {
        "issue": issue.number,
        "title": issue.title,
        "state": issue.state,
        "old_labels": list(issue.labels),
        "labels": list(desired),
        "remove_labels": sorted(remove),
        "add_labels": sorted(add),
        "changed": bool(remove or add),
        "dry_run": dry_run,
    }


def migrate_legacy_tasks(
    issue_ref: str | None = None,
    *,
    dry_run: bool = False,
    limit: int = 500,
    cwd: Path | None = None,
) -> list[Mapping[str, object]]:
    if issue_ref is not None:
        return [migrate_issue_labels(issue_ref, dry_run=dry_run, cwd=cwd)]
    return [
        migrate_issue_labels(str(issue["number"]), dry_run=dry_run, cwd=cwd)
        for issue in list_legacy_task_issues(limit=limit, cwd=cwd)
    ]


def set_issue_state(
    issue_ref: str,
    *,
    current_labels: Sequence[str],
    status: str,
    phase: str,
    cwd: Path | None = None,
) -> None:
    latest_labels = fetch_issue_labels(issue_ref, cwd=cwd)
    remove, add = _label_transition_diff(latest_labels, status=status, phase=phase)
    if not remove and not add:
        return
    if remove:
        gh_run(["issue", "edit", issue_ref, "--remove-label", ",".join(sorted(remove))], cwd=cwd)
    if add:
        gh_run(["issue", "edit", issue_ref, "--add-label", ",".join(sorted(add))], cwd=cwd)


def comment(issue_or_pr_ref: str, body: str, *, cwd: Path | None = None) -> None:
    if comment_exists(issue_or_pr_ref, body, cwd=cwd):
        return
    gh_run(["issue", "comment", issue_or_pr_ref, "--body", body], cwd=cwd)


def fetch_issue_labels(issue_ref: str, *, cwd: Path | None = None) -> tuple[str, ...]:
    payload = gh_json(["issue", "view", issue_ref, "--json", "labels"], cwd=cwd)
    if not isinstance(payload, Mapping):
        raise ValueError("gh issue view returned non-object JSON")
    return tuple(_label_names(payload.get("labels", [])))


def comment_exists(issue_or_pr_ref: str, body: str, *, cwd: Path | None = None) -> bool:
    payload = gh_json(["issue", "view", issue_or_pr_ref, "--json", "comments"], cwd=cwd)
    if not isinstance(payload, Mapping):
        raise ValueError("gh issue view returned non-object JSON")
    return any(
        isinstance(comment.get("body"), str) and comment["body"] == body
        for comment in _comments(payload.get("comments", []))
    )


def _label_transition_diff(
    current_labels: Sequence[str],
    *,
    status: str,
    phase: str,
) -> tuple[set[str], set[str]]:
    desired = set(transition_labels(current_labels, status=status, phase=phase))
    current = set(current_labels)
    remove = current.intersection((*STATUS_LABELS, *PHASE_LABELS)) - desired
    add = desired - current
    return remove, add


def _migration_label_diff(
    current_labels: Sequence[str],
    desired_labels: Sequence[str],
) -> tuple[set[str], set[str]]:
    current = set(current_labels)
    desired = set(desired_labels)
    managed = set(STATUS_LABELS).union(PHASE_LABELS)
    remove = {
        label
        for label in current
        if label not in desired
        and (label in managed or _is_legacy_task_label(label))
    }
    add = desired - current
    return remove, add


def _has_legacy_task_label(labels: Sequence[str]) -> bool:
    return any(_is_legacy_task_label(label) for label in labels)


def _is_legacy_task_label(label: str) -> bool:
    normalized = label.lower()
    return any(normalized.startswith(prefix) for prefix in LEGACY_TASK_LABEL_PREFIXES)


def _label_names(labels: object) -> list[str]:
    if not isinstance(labels, list):
        return []
    names: list[str] = []
    for label in labels:
        if isinstance(label, str):
            names.append(label)
        elif isinstance(label, Mapping):
            name = label.get("name")
            if isinstance(name, str):
                names.append(name)
    return names


def _comments(comments: object) -> list[Mapping[str, object]]:
    if not isinstance(comments, list):
        return []
    return [comment for comment in comments if isinstance(comment, Mapping)]


def _validate_legacy_migration_plan(
    issues: Sequence[Mapping[str, object]],
) -> None:
    invalid_issues: list[int] = []
    for issue in issues:
        issue_labels = _label_names(issue.get("labels", []))
        issue_state = str(issue.get("state", "OPEN"))
        expected = migrate_task_labels(issue_labels, issue_state=issue_state)
        if not _labels_include_single_status_and_phase(expected):
            issue_number = issue.get("number")
            if isinstance(issue_number, int):
                invalid_issues.append(issue_number)
            elif isinstance(issue_number, str) and issue_number.isdigit():
                invalid_issues.append(int(issue_number))
    if invalid_issues:
        raise RuntimeError(
            f"legacy migration plan is incomplete for issues: {invalid_issues}"
        )


def _labels_include_single_status_and_phase(labels: Sequence[str]) -> bool:
    status_count = len([label for label in labels if label in STATUS_LABELS])
    phase_count = len([label for label in labels if label in PHASE_LABELS])
    return status_count == 1 and phase_count == 1
