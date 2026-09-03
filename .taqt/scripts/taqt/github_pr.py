import argparse
import json
import subprocess
from pathlib import Path

from .github_labels import enabled_error
from .github_merge import _checks_command, run_checks
from .task_store import block_task, issue_branch, issue_ref, load_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-github-pr")
    parser.add_argument("task")
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--base", default="main")
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--watch-checks", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--required-checks", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--check-interval", type=int, default=10)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    task_path, task = load_task(args.task)
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
    print(
        " ".join(
            _checks_command(
                repo=str(source["repo"]),
                selector=branch,
                watch=args.watch_checks,
                required=args.required_checks,
                interval=args.check_interval,
            )
        )
    )
    if not args.execute:
        return 0
    label_error = enabled_error(task)
    if label_error:
        block_task(task_path, task, label_error)
        print(label_error)
        return 2
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
        result = subprocess.run(edit_command, cwd=args.workspace, check=False).returncode
    else:
        result = subprocess.run(command, cwd=args.workspace, check=False).returncode
    if result != 0 or not args.watch_checks:
        return result

    pr = existing or _find_existing_pr(repo=str(source["repo"]), branch=branch, cwd=args.workspace)
    if pr is None:
        print(f"No pull request found for branch {branch!r}.")
        return 1
    return run_checks(
        repo=str(source["repo"]),
        selector=str(pr["number"]),
        cwd=args.workspace,
        watch=True,
        required=args.required_checks,
        interval=args.check_interval,
    )


def _quote(value: str) -> str:
    if not any(char.isspace() for char in value):
        return value
    return repr(value)


def _find_existing_pr(*, repo: str, branch: str, cwd: Path) -> dict[str, object] | None:
    completed = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--head",
            branch,
            "--state",
            "open",
            "--json",
            "number,url",
        ],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return None
    payload = json.loads(completed.stdout)
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    return None


if __name__ == "__main__":
    raise SystemExit(main())
