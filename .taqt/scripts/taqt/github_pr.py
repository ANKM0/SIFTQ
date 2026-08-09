import argparse
import json
import subprocess
from pathlib import Path

from .task_store import issue_branch, issue_ref, load_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-github-pr")
    parser.add_argument("task")
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--base", default="main")
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    _path, task = load_task(args.task)
    source = task["source"]
    branch = issue_branch(task)
    title = f"#{source['issue_number']} development feedback loop"
    body = (
        f"Implements {issue_ref(task)} through taqt development feedback loop.\n\n"
        f"- task: `{task['id']}`\n"
        f"- loop: `{task['loop']}`\n"
        f"- run state: `{task.get('run', {}).get('state_path')}`\n"
    )
    command = [
        "gh",
        "pr",
        "create",
        "--repo",
        str(source["repo"]),
        "--base",
        args.base,
        "--head",
        branch,
        "--title",
        title,
        "--body",
        body,
    ]
    if args.draft:
        command.append("--draft")
    print(" ".join(_quote(part) for part in command))
    if not args.execute:
        return 0
    existing = _find_existing_pr(repo=str(source["repo"]), branch=branch, cwd=args.workspace)
    if existing is not None:
        edit_command = [
            "gh",
            "pr",
            "edit",
            str(existing["number"]),
            "--repo",
            str(source["repo"]),
            "--title",
            title,
            "--body",
            body,
        ]
        return subprocess.run(edit_command, cwd=args.workspace, check=False).returncode
    return subprocess.run(command, cwd=args.workspace, check=False).returncode


def _quote(value: str) -> str:
    if not any(char.isspace() for char in value):
        return value
    return repr(value)


def _find_existing_pr(*, repo: str, branch: str, cwd: Path) -> dict[str, object] | None:
    completed = subprocess.run(
        ["gh", "pr", "view", "--repo", repo, "--head", branch, "--json", "number,url"],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return None
    payload = json.loads(completed.stdout)
    return payload if isinstance(payload, dict) else None


if __name__ == "__main__":
    raise SystemExit(main())
