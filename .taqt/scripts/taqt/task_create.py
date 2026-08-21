import argparse
import json
import subprocess
from pathlib import Path

from .github_labels import ENABLED_LABEL
from .task_store import DEFAULT_TASK_ROOT, create_issue_task, upsert_issue_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-task-create")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--issue", required=True, type=int)
    parser.add_argument("--loop", default="development_feedback_loop")
    parser.add_argument("--priority", default="normal", choices=["low", "normal", "high"])
    parser.add_argument("--requirement")
    parser.add_argument("--branch-summary")
    parser.add_argument("--id")
    parser.add_argument("--task-root", type=Path, default=DEFAULT_TASK_ROOT)
    args = parser.parse_args(argv)

    issue = _fetch_issue(args.repo, args.issue)
    if issue is None:
        print(f"Could not verify {args.repo}#{args.issue} labels; refusing to create a taqt task.")
        return 2
    if ENABLED_LABEL not in issue["labels"]:
        print(f"{args.repo}#{args.issue} does not have {ENABLED_LABEL}; refusing to create a taqt task.")
        return 2
    if args.id:
        path, _task = create_issue_task(
            repo=args.repo,
            issue_number=args.issue,
            loop=args.loop,
            priority=args.priority,
            requirement=args.requirement,
            branch_summary=args.branch_summary or issue.get("title"),
            task_id=args.id,
            issue_title=issue.get("title"),
            issue_body=issue.get("body"),
            issue_labels=issue.get("labels"),
            task_root=args.task_root,
        )
    else:
        path, _task, _created = upsert_issue_task(
            repo=args.repo,
            issue_number=args.issue,
            loop=args.loop,
            priority=args.priority,
            requirement=args.requirement,
            branch_summary=args.branch_summary,
            issue_title=issue.get("title"),
            issue_body=issue.get("body"),
            issue_labels=issue.get("labels"),
            task_root=args.task_root,
        )
    print(path)
    return 0


def _fetch_issue(repo: str, issue_number: int) -> dict[str, object] | None:
    completed = subprocess.run(
        [
            "gh",
            "issue",
            "view",
            str(issue_number),
            "--repo",
            repo,
            "--json",
            "title,body,labels",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return None
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    labels = [
        str(label.get("name"))
        for label in payload.get("labels", [])
        if isinstance(label, dict) and label.get("name")
    ]
    return {
        "title": payload.get("title"),
        "body": payload.get("body"),
        "labels": labels,
    }


if __name__ == "__main__":
    raise SystemExit(main())
