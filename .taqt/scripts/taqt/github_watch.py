from __future__ import annotations

import argparse
import json
import subprocess

from .task_store import create_issue_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-github-watch")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--label", action="append", default=[])
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--loop", default="development_feedback_loop")
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
        "number,title,labels",
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
        if args.dry_run:
            print(f"ISSUE-{issue_number}: {issue['title']}")
            continue
        path, _task = create_issue_task(
            repo=args.repo,
            issue_number=issue_number,
            loop=args.loop,
        )
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
