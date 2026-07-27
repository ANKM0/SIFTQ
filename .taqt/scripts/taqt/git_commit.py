from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from .task_store import issue_branch, load_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-git-commit")
    parser.add_argument("task")
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--message")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    _path, task = load_task(args.task)
    subject = args.message or _default_subject(task)
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=args.workspace,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if status.returncode != 0:
        print(status.stderr, end="")
        return status.returncode
    if not status.stdout.strip():
        print("No changes to commit.")
        return 0

    commands = [
        ["git", "add", "-A"],
        ["git", "commit", "-m", subject],
    ]
    for command in commands:
        print(" ".join(command))
    if not args.execute:
        return 0
    for command in commands:
        completed = subprocess.run(command, cwd=args.workspace, check=False)
        if completed.returncode != 0:
            return completed.returncode
    print(issue_branch(task))
    return 0


def _default_subject(task: dict[str, object]) -> str:
    source = task["source"]
    issue_number = source["issue_number"]
    return f"#{issue_number} feat(taqt): implement development feedback loop task"


if __name__ == "__main__":
    raise SystemExit(main())
