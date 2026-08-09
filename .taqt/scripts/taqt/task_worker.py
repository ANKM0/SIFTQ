import argparse
import os
import subprocess
import sys
from pathlib import Path

from .task_store import (
    DEFAULT_TASK_ROOT,
    PRIORITY_ORDER,
    decomposition_errors,
    issue_branch,
    list_tasks,
    readiness_errors,
    readiness_warnings,
    save_task,
    triage_task,
)
from .self_improvement import request_self_improvement


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-task-worker")
    parser.add_argument("--task-root", type=Path, default=DEFAULT_TASK_ROOT)
    parser.add_argument("--worktree-root", type=Path, default=Path(".taqt/worktrees"))
    parser.add_argument("--loop-root", type=Path, default=Path(".taqt/loops"))
    parser.add_argument("--runs-root", type=Path, default=Path(".taqt/runs"))
    parser.add_argument("--base", default="main")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--worker-id", default="local-worker")
    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--cleanup-worktree", action="store_true")
    parser.add_argument("--delete-local-branch", action="store_true")
    parser.add_argument("--delete-remote-branch", action="store_true")
    parser.add_argument("--force-worktree", action="store_true")
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
        errors = readiness_errors(task, workspace=Path("."))
        if errors:
            reason = "; ".join(errors)
            print(f"{task['id']}: not ready: {reason}")
            if args.execute:
                triage_task(task_path, task, reason)
                request_self_improvement(
                    task_path=task_path,
                    task=task,
                    reason=reason,
                    event="readiness_failed",
                    runs_root=args.runs_root,
                    workspace=Path("."),
                )
                save_task(task_path, task)
            continue
        errors = decomposition_errors(task, workspace=Path("."))
        if errors:
            reason = "; ".join(errors)
            print(f"{task['id']}: not decomposed enough: {reason}")
            if args.execute and task.get("phase") != "decomposed":
                triage_task(task_path, task, reason)
            continue
        for warning in readiness_warnings(task, workspace=Path(".")):
            print(f"{task['id']}: readiness warning: {warning}")

        worktree_command = ["git", "worktree", "add", "-B", issue_branch(task), str(worktree), args.base]
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
    if merge:
        command.append("--merge")
    if cleanup_worktree:
        command.append("--cleanup-worktree")
    if delete_local_branch:
        command.append("--delete-local-branch")
    if delete_remote_branch:
        command.append("--delete-remote-branch")
    if force_worktree:
        command.append("--force-worktree")
    if execute:
        command.append("--execute")
    return command


if __name__ == "__main__":
    raise SystemExit(main())
