import argparse
import json
import subprocess
from pathlib import Path

from .github_labels import ENABLED_LABEL
from .task_store import DEFAULT_TASK_ROOT, upsert_issue_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-github-watch")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--label", action="append", default=[])
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--loop", default="development_feedback_loop")
    parser.add_argument("--priority", default="normal", choices=["low", "normal", "high"])
    parser.add_argument("--task-root", type=Path, default=DEFAULT_TASK_ROOT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    gh_args = [
        "gh",
        "issue",
        "list",
        "--repo",
        args.repo,
        "--state",
        "open",
        "--limit",
        str(args.limit),
        "--json",
        "number,title,body,labels",
        "--label",
        ENABLED_LABEL,
    ]
    for label in args.label:
        gh_args.extend(["--label", label])

    completed = subprocess.run(
        gh_args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stderr, end="")
        return completed.returncode

    issues = json.loads(completed.stdout)
    for issue in issues:
        issue_number = int(issue["number"])
        labels = [
            str(label.get("name"))
            for label in issue.get("labels", [])
            if isinstance(label, dict) and label.get("name")
        ]
        if args.dry_run:
            print(f"ISSUE-{issue_number}: {issue['title']} [{', '.join(labels)}]")
            continue
        path, _task, created = upsert_issue_task(
            repo=args.repo,
            issue_number=issue_number,
            loop=args.loop,
            priority=args.priority,
            issue_title=issue.get("title"),
            issue_body=issue.get("body"),
            issue_labels=labels,
            task_root=args.task_root,
        )
        action = "created" if created else "updated"
        print(f"{action}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
