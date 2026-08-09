import argparse
import json
import subprocess
from pathlib import Path

from .task_store import issue_branch, load_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-github-merge")
    parser.add_argument("task")
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--strategy", choices=["squash", "merge", "rebase"], default="squash")
    parser.add_argument("--delete-branch", action="store_true")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--watch-checks", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--required-checks", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--check-interval", type=int, default=10)
    parser.add_argument("--allow-draft", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    _path, task = load_task(args.task)
    source = task["source"]
    repo = str(source["repo"])
    branch = issue_branch(task)
    selector = branch

    checks_command = _checks_command(
        repo=repo,
        selector=selector,
        watch=args.watch_checks,
        required=args.required_checks,
        interval=args.check_interval,
    )
    merge_command = _merge_command(
        repo=repo,
        selector=selector,
        strategy=args.strategy,
        delete_branch=args.delete_branch,
        auto=args.auto,
    )
    print(" ".join(checks_command))
    print(" ".join(merge_command))
    if not args.execute:
        return 0

    pr = find_pr(repo=repo, branch=branch, cwd=args.workspace)
    if pr is None:
        print(f"No pull request found for branch {branch!r}.")
        return 1
    if pr.get("isDraft") and not args.allow_draft:
        print(f"Refusing to merge draft PR #{pr['number']}.")
        return 2

    selector = str(pr["number"])
    if args.watch_checks:
        checks = _checks_command(
            repo=repo,
            selector=selector,
            watch=True,
            required=args.required_checks,
            interval=args.check_interval,
        )
        completed = subprocess.run(checks, cwd=args.workspace, check=False)
        if completed.returncode != 0:
            return completed.returncode

    merge = _merge_command(
        repo=repo,
        selector=selector,
        strategy=args.strategy,
        delete_branch=args.delete_branch,
        auto=args.auto,
    )
    return subprocess.run(merge, cwd=args.workspace, check=False).returncode


def find_pr(*, repo: str, branch: str, cwd: Path) -> dict[str, object] | None:
    completed = subprocess.run(
        ["gh", "pr", "view", "--repo", repo, "--head", branch, "--json", "number,url,isDraft"],
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


def _checks_command(
    *,
    repo: str,
    selector: str,
    watch: bool,
    required: bool,
    interval: int,
) -> list[str]:
    command = ["gh", "pr", "checks", selector, "--repo", repo]
    if required:
        command.append("--required")
    if watch:
        command.extend(["--watch", "--fail-fast", "--interval", str(interval)])
    return command


def _merge_command(
    *,
    repo: str,
    selector: str,
    strategy: str,
    delete_branch: bool,
    auto: bool,
) -> list[str]:
    command = ["gh", "pr", "merge", selector, "--repo", repo, f"--{strategy}"]
    if delete_branch:
        command.append("--delete-branch")
    if auto:
        command.append("--auto")
    return command


if __name__ == "__main__":
    raise SystemExit(main())
