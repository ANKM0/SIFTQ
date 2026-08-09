import argparse
import subprocess
from pathlib import Path

from .task_store import (
    DEFAULT_TASK_ROOT,
    complete_parent_if_children_done,
    complete_task,
    issue_branch,
    is_stale_task,
    list_tasks,
    load_document,
    load_task,
    recover_stale_task,
    task_path,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-task-cleanup")
    parser.add_argument("task", nargs="?")
    parser.add_argument("--task-root", type=Path, default=DEFAULT_TASK_ROOT)
    parser.add_argument("--worktree-root", type=Path, default=Path(".taqt/worktrees"))
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--delete-local-branch", action="store_true")
    parser.add_argument("--delete-remote-branch", action="store_true")
    parser.add_argument("--mark-done", action="store_true")
    parser.add_argument("--sync-parent", action="store_true")
    parser.add_argument("--recover-stale", action="store_true")
    parser.add_argument("--stale-minutes", type=int, default=60)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    if args.recover_stale:
        return _recover_stale(task_root=args.task_root, stale_minutes=args.stale_minutes, execute=args.execute)
    if not args.task:
        print("task is required unless --recover-stale is used")
        return 2

    task_file, task = load_task(args.task, args.task_root)
    worktree = args.workspace or args.worktree_root / str(task["id"])
    branch = issue_branch(task)
    commands = [["git", "worktree", "remove", str(worktree)]]
    if args.delete_local_branch:
        commands.append(["git", "branch", "-d", branch])
    if args.delete_remote_branch:
        commands.append(["git", "push", args.remote, "--delete", branch])

    for command in commands:
        print(" ".join(command))
    if args.mark_done:
        print(f"mark done: {task['id']}")
    if args.sync_parent:
        print(f"sync parent if all child tasks are done: {task['id']}")
    if not args.execute:
        return 0

    if worktree.resolve() == Path(".").resolve():
        print("Refusing to remove repository root as a worktree.")
        return 2
    if not worktree.exists():
        print(f"Worktree does not exist: {worktree}")
    else:
        completed = subprocess.run(commands[0], check=False)
        if completed.returncode != 0:
            return completed.returncode

    for command in commands[1:]:
        completed = subprocess.run(command, check=False)
        if completed.returncode != 0:
            return completed.returncode

    if args.mark_done:
        complete_task(task_file, task, reason=None)
    if args.sync_parent:
        _sync_parent(task, task_root=args.task_root)
    return 0


def _recover_stale(*, task_root: Path, stale_minutes: int, execute: bool) -> int:
    recovered = 0
    for task_file, task in list_tasks(task_root):
        worker = task.get("worker") if isinstance(task.get("worker"), dict) else {}
        if not is_stale_task(task, stale_minutes=stale_minutes):
            continue
        print(f"recover stale task: {task['id']} worker={worker.get('id')}")
        recovered += 1
        if execute:
            recover_stale_task(task_file, task, stale_minutes=stale_minutes)
    if recovered == 0:
        print("No stale running taqt tasks.")
        return 0
    return 0


def _sync_parent(task: dict[str, object], *, task_root: Path) -> None:
    slice_info = task.get("slice")
    parent_id = slice_info.get("parent_task") if isinstance(slice_info, dict) else None
    if not isinstance(parent_id, str) or not parent_id:
        return
    parent_file = task_path(parent_id, task_root)
    if not parent_file.exists():
        return
    parent = load_document(parent_file)
    complete_parent_if_children_done(parent_file, parent, task_root=task_root)


if __name__ == "__main__":
    raise SystemExit(main())
