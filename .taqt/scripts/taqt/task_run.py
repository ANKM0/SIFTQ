import argparse
import getpass
import os
from pathlib import Path

from loop.runner import run_loop
from loop.state import utc_now

from .github_labels import enabled_error
from .profiles import load_profiles, resolve_codex_home, resolve_profile
from .self_improvement import request_self_improvement
from .task_store import (
    DEFAULT_TASK_ROOT,
    block_task,
    decomposition_errors,
    load_task,
    next_pending_task,
    readiness_errors,
    readiness_warnings,
    save_task,
    triage_task,
)

TERMINAL_STATUSES = {"blocked", "done", "failed"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-task-run")
    parser.add_argument("task", nargs="?")
    parser.add_argument("--task-root", type=Path, default=DEFAULT_TASK_ROOT)
    parser.add_argument("--loop-root", type=Path, default=Path(".taqt/loops"))
    parser.add_argument("--runs-root", type=Path, default=Path(".taqt/runs"))
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--worker-id", default="local")
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--profile")
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--skip-readiness-check", action="store_true")
    args = parser.parse_args(argv)

    try:
        profile = resolve_profile(args.loop_root, args.profile)
        profiles = load_profiles(args.loop_root)
    except ValueError as error:
        print(error)
        return 2
    profile_spec = profiles[profile]

    if args.task:
        task_path, task = load_task(args.task, args.task_root)
    else:
        selected = next_pending_task(args.task_root)
        if selected is None:
            print("No pending taqt tasks.")
            return 0
        task_path, task = selected

    lock_error = _lock_error(task, args.worker_id)
    if lock_error:
        print(lock_error)
        return 2
    if args.resume:
        resume_error = _resume_error(task, args.resume)
        if resume_error:
            print(resume_error)
            return 2
    label_error = enabled_error(task)
    if label_error:
        block_task(task_path, task, label_error)
        print(f"Task {task['id']} is blocked: {label_error}")
        return 2
    if not args.skip_readiness_check and task.get("status") != "running":
        errors = readiness_errors(task, workspace=args.workspace)
        if errors:
            reason = "; ".join(errors)
            triage_task(task_path, task, reason)
            request = request_self_improvement(
                task_path=task_path,
                task=task,
                reason=reason,
                event="readiness_failed",
                runs_root=args.runs_root,
                workspace=args.workspace,
            )
            save_task(task_path, task)
            print(f"Task {task['id']} is not ready: {reason}")
            print(f"Self-improvement requested: {request['request_path']}")
            return 2
        errors = decomposition_errors(task, workspace=args.workspace)
        if errors:
            reason = "; ".join(errors)
            if task.get("phase") != "decomposed":
                triage_task(task_path, task, reason)
            print(f"Task {task['id']} is not decomposed enough: {reason}")
            return 2
        warnings = readiness_warnings(task, workspace=args.workspace)
        for warning in warnings:
            print(f"Task {task['id']} readiness warning: {warning}")

    loop_name = str(profile_spec["loop"])
    loop_path = args.loop_root / f"{loop_name}.yaml"
    child_environment: dict[str, str] = {}
    if args.codex_home is not None:
        codex_home = resolve_codex_home(
            profile_spec,
            args.workspace,
            profile=profile,
            override=args.codex_home,
        )
        child_environment["CODEX_HOME"] = str(codex_home)
    env_keys = profile_spec.get("env_keys", [])
    if not isinstance(env_keys, list) or not all(isinstance(key, str) and key for key in env_keys):
        print(f"taqt profile {profile} has invalid env_keys.")
        return 2
    for env_key in env_keys:
        api_key = os.environ.get(env_key) or _prompt_api_key(env_key)
        if not api_key:
            print(f"{env_key} is required.")
            return 2
        child_environment[env_key] = api_key

    task["status"] = "running"
    task["worker"] = {"id": args.worker_id, "started_at": utc_now(), "heartbeat_at": utc_now()}
    save_task(task_path, task)

    result = run_loop(
        loop_path=loop_path,
        task_path=task_path,
        workspace=args.workspace,
        runs_root=args.runs_root,
        resume_dir=args.resume,
        child_environment=child_environment,
    )

    label_error = enabled_error(task)
    if label_error:
        block_task(task_path, task, label_error)
        print(f"Task {task['id']} is blocked: {label_error}")
        return 2

    if result["status"] == "done":
        task["status"] = "done"
        task["blocked_reason"] = None
    elif result["status"] == "human":
        task["status"] = "blocked"
        task["blocked_reason"] = "human escalation required"
    else:
        task["status"] = result["status"]
        task["blocked_reason"] = f"loop ended with status {result['status']}"
    task["phase"] = result.get("phase") or result["status"]
    task["run"] = {
        "id": Path(result["run_dir"]).name,
        "state_path": str(Path(result["run_dir"]) / "state.json"),
        "events_path": str(Path(result["run_dir"]) / "events.jsonl"),
    }
    task["worker"] = {"id": None, "heartbeat_at": None}
    if task["status"] in {"blocked", "failed"}:
        request_self_improvement(
            task_path=task_path,
            task=task,
            reason=str(task.get("blocked_reason") or result["status"]),
            event=f"loop_{result['status']}",
            runs_root=args.runs_root,
            workspace=args.workspace,
            run_dir=Path(result["run_dir"]),
        )
    save_task(task_path, task)
    print(result["run_dir"])
    return 0 if result["status"] in {"done", "human"} else 1


def _lock_error(task: dict[str, object], worker_id: str) -> str | None:
    if task.get("status") != "running":
        return None
    worker = task.get("worker")
    current_worker = worker.get("id") if isinstance(worker, dict) else None
    if current_worker in {None, worker_id}:
        return None
    return f"Task {task['id']} is already running by worker {current_worker}."


def _resume_error(task: dict[str, object], resume_dir: Path) -> str | None:
    run = task.get("run")
    expected_id = run.get("id") if isinstance(run, dict) else None
    if expected_id and expected_id != resume_dir.name:
        return f"Resume run {resume_dir.name} does not match task run {expected_id}."
    state_path = resume_dir / "state.json"
    if not state_path.exists():
        return f"Resume run is missing state.json: {resume_dir}"
    if task.get("status") in TERMINAL_STATUSES and not expected_id:
        return f"Task {task['id']} has terminal status {task.get('status')} and no resumable run."
    return None


def _prompt_api_key(env_key: str) -> str:
    try:
        return getpass.getpass(f"{env_key}: ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
