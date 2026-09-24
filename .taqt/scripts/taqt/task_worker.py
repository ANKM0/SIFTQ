import argparse
import os
import subprocess
import sys
from pathlib import Path

from .git_worktree import build_worktree_command
from .github_labels import enabled_error
from .self_improvement import request_self_improvement
from .task_preflight import preflight_task
from .task_store import (
    DEFAULT_TASK_ROOT,
    DEFAULT_WORKTREE_ROOT,
    PRIORITY_ORDER,
    block_task,
    list_tasks,
    readiness_warnings,
    save_task,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-task-worker")
    parser.add_argument("--task-root", type=Path, default=DEFAULT_TASK_ROOT)
    parser.add_argument("--worktree-root", type=Path, default=DEFAULT_WORKTREE_ROOT)
    parser.add_argument("--loop-root", type=Path, default=Path(".taqt/loops"))
    parser.add_argument("--runs-root", type=Path, default=Path(".taqt/runs"))
    parser.add_argument("--base", default="main")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--worker-id", default="local-worker")
    parser.add_argument("--merge", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--cleanup-worktree", action=argparse.BooleanOptionalAction, default=True
    )
    parser.add_argument(
        "--delete-local-branch", action=argparse.BooleanOptionalAction, default=True
    )
    parser.add_argument(
        "--delete-remote-branch", action=argparse.BooleanOptionalAction, default=False
    )
    parser.add_argument(
        "--force-worktree", action=argparse.BooleanOptionalAction, default=True
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    selected = _select_pending(args.task_root, limit=args.limit or args.jobs)
    if not selected:
        print("No pending taqt tasks.")
        return 0

    planned = 0
    processes: list[subprocess.Popen[bytes]] = []
    for task_path, task in selected:
        worker_id = f"{args.worker_id}-{task['id']}"
        worktree = args.worktree_root / str(task["id"])
        if args.execute:
            label_error = enabled_error(task)
            if label_error:
                print(f"{task['id']}: {label_error}")
                block_task(task_path, task, label_error)
                continue
        errors = preflight_task(
            task_path,
            task,
            workspace=Path("."),
            runs_root=args.runs_root,
            execute=args.execute,
        )
        if errors:
            print(f"{task['id']}: not ready: {'; '.join(errors)}")
            continue
        for warning in readiness_warnings(task, workspace=Path(".")):
            print(f"{task['id']}: readiness warning: {warning}")

        worktree_command = build_worktree_command(
            task, base=args.base, worktree_root=args.worktree_root
        )
        auto_command = _auto_command(
            task_path=task_path,
            worktree=worktree,
            loop_root=args.loop_root,
            runs_root=args.runs_root,
            worker_id=worker_id,
            remote=args.remote,
            base=args.base,
            merge=args.merge,
            cleanup_worktree=args.cleanup_worktree,
            delete_local_branch=args.delete_local_branch,
            delete_remote_branch=args.delete_remote_branch,
            force_worktree=args.force_worktree,
            execute=args.execute,
        )
        print(" ".join(worktree_command))
        print(" ".join(auto_command))
        planned += 1
        if not args.execute:
            continue

        task["status"] = "running"
        task["phase"] = "queued"
        task["worker"] = {"id": worker_id, "heartbeat_at": None}
        save_task(task_path, task)

        worktree.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(worktree_command, check=False)
        if completed.returncode != 0:
            task["status"] = "failed"
            task["blocked_reason"] = f"git worktree failed with exit code {completed.returncode}"
            task["worker"] = {"id": None, "heartbeat_at": None}
            request_self_improvement(
                task_path=task_path,
                task=task,
                reason=str(task["blocked_reason"]),
                event="worktree_failed",
                runs_root=args.runs_root,
                workspace=Path("."),
            )
            save_task(task_path, task)
            continue
        env = dict(os.environ)
        env["PYTHONPATH"] = ".taqt/scripts"
        processes.append(subprocess.Popen(auto_command, env=env))
        if len(processes) >= args.jobs:
            break

    exit_code = 0
    for process in processes:
        exit_code = max(exit_code, process.wait())
    if planned == 0:
        return 2
    return exit_code


def _select_pending(task_root: Path, *, limit: int) -> list[tuple[Path, dict[str, object]]]:
    pending = [
        (path, task)
        for path, task in list_tasks(task_root)
        if task.get("status") == "pending" and task.get("phase") != "decomposed"
    ]
    return sorted(
        pending,
        key=lambda item: (
            PRIORITY_ORDER.get(str(item[1].get("priority")), PRIORITY_ORDER["normal"]),
            item[0].name,
        ),
    )[:limit]


def _auto_command(
    *,
    task_path: Path,
    worktree: Path,
    loop_root: Path,
    runs_root: Path,
    worker_id: str,
    remote: str,
    base: str,
    merge: bool,
    cleanup_worktree: bool,
    delete_local_branch: bool,
    delete_remote_branch: bool,
    force_worktree: bool,
    execute: bool,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "taqt.task_auto",
        str(task_path.resolve()),
        "--workspace",
        str(worktree),
        "--loop-root",
        str(loop_root),
        "--runs-root",
        str(runs_root),
        "--worker-id",
        worker_id,
        "--remote",
        remote,
        "--base",
        base,
    ]
    command.append("--merge" if merge else "--no-merge")
    command.append("--cleanup-worktree" if cleanup_worktree else "--no-cleanup-worktree")
    command.append(
        "--delete-local-branch" if delete_local_branch else "--no-delete-local-branch"
    )
    command.append(
        "--delete-remote-branch" if delete_remote_branch else "--no-delete-remote-branch"
    )
    command.append("--force-worktree" if force_worktree else "--no-force-worktree")
    if execute:
        command.append("--execute")
    return command


if __name__ == "__main__":
    raise SystemExit(main())
