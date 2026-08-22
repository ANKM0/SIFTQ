import argparse
import json
import subprocess
from pathlib import Path

from .github_labels import enabled_error
from .task_store import block_task, issue_branch, load_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-git-commit")
    parser.add_argument("task")
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--message")
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--allow-branch-mismatch", action="store_true")
    parser.add_argument("--allow-unverified-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    task_path, task = load_task(args.task)
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

    add_command = ["git", "add", "-A", *args.include] if args.include else ["git", "add", "-A"]
    commands = [
        add_command,
        ["git", "commit", "-m", subject],
    ]
    for command in commands:
        print(" ".join(command))
    if not args.execute:
        return 0
    label_error = enabled_error(task)
    if label_error:
        block_task(task_path, task, label_error)
        print(label_error)
        return 2
    if not args.allow_unverified_run:
        run_check = _ensure_verified_run(task)
        if run_check != 0:
            return run_check
    if not args.allow_branch_mismatch:
        branch_check = _ensure_expected_branch(args.workspace, issue_branch(task))
        if branch_check != 0:
            return branch_check
    if args.include:
        scope_check = _ensure_changes_within_includes(status.stdout, args.include)
        if scope_check != 0:
            return scope_check
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


def _ensure_expected_branch(workspace: Path, expected: str) -> int:
    completed = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=workspace,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stderr, end="")
        return completed.returncode
    current = completed.stdout.strip()
    if current != expected:
        print(f"Refusing to commit on branch {current!r}; expected {expected!r}.")
        return 2
    return 0


def _ensure_verified_run(task: dict[str, object]) -> int:
    run = task.get("run")
    state_path = run.get("state_path") if isinstance(run, dict) else None
    if not state_path:
        print("Refusing to commit without a verified taqt run state.")
        return 2
    path = Path(str(state_path))
    if not path.exists():
        print(f"Refusing to commit because run state does not exist: {path}")
        return 2
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("status") != "done":
        print(f"Refusing to commit because taqt run status is {state.get('status')!r}.")
        return 2
    return 0


def _ensure_changes_within_includes(status_output: str, includes: list[str]) -> int:
    prefixes = [include.rstrip("/") + "/" for include in includes]
    exact = set(includes)
    for line in status_output.splitlines():
        if not line:
            continue
        path = line[3:] if len(line) > 3 else line
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[1]
        if path in exact or any(path.startswith(prefix) for prefix in prefixes):
            continue
        print(f"Refusing to commit path outside --include scope: {path}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
