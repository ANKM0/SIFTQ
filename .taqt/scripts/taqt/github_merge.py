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
        checks_result = run_checks(
            repo=repo,
            selector=selector,
            cwd=args.workspace,
            watch=True,
            required=args.required_checks,
            interval=args.check_interval,
        )
        if checks_result != 0:
            return checks_result

    merge = _merge_command(
        repo=repo,
        selector=selector,
        strategy=args.strategy,
        delete_branch=args.delete_branch,
        auto=args.auto,
    )
    return subprocess.run(merge, cwd=args.workspace, check=False).returncode


def run_checks(
    *,
    repo: str,
    selector: str,
    cwd: Path,
    watch: bool,
    required: bool,
    interval: int,
) -> int:
    checks = _checks_command(
        repo=repo,
        selector=selector,
        watch=watch,
        required=required,
        interval=interval,
    )
    completed = subprocess.run(
        checks,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode == 0:
        print(completed.stdout, end="")
        print(completed.stderr, end="")
        return 0
    if required and _is_missing_required_checks(completed):
        fallback = _checks_command(
            repo=repo,
            selector=selector,
            watch=watch,
            required=False,
            interval=interval,
        )
        print("No required checks reported; falling back to all PR checks.")
        print(" ".join(fallback))
        fallback_completed = subprocess.run(
            fallback,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        print(fallback_completed.stdout, end="")
        print(fallback_completed.stderr, end="")
        return fallback_completed.returncode
    print(completed.stdout, end="")
    print(completed.stderr, end="")
    return completed.returncode


def _is_missing_required_checks(completed: subprocess.CompletedProcess[str]) -> bool:
    output = f"{completed.stdout}\n{completed.stderr}".lower()
    return "no required checks reported" in output


def find_pr(*, repo: str, branch: str, cwd: Path) -> dict[str, object] | None:
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
            "number,url,isDraft",
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
