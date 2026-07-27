from __future__ import annotations

import argparse
import subprocess

from .task_store import load_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-github-sync")
    parser.add_argument("task")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    _path, task = load_task(args.task)
    source = task["source"]
    issue_ref = f"{source['repo']}#{source['issue_number']}"
    body = (
        "taqt task update.\n\n"
        f"- task: `{task['id']}`\n"
        f"- status: `{task['status']}`\n"
        f"- phase: `{task['phase']}`\n"
        f"- run state: `{task.get('run', {}).get('state_path')}`\n"
    )
    command = [
        "gh",
        "issue",
        "comment",
        str(source["issue_number"]),
        "--repo",
        str(source["repo"]),
        "--body",
        body,
    ]
    if not args.execute:
        print(f"{issue_ref}:")
        print(body)
        return 0
    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
