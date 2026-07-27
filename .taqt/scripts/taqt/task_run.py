from __future__ import annotations

import argparse
from pathlib import Path

from loop.runner import run_loop
from loop.state import utc_now

from .task_store import load_task, save_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-task-run")
    parser.add_argument("task")
    parser.add_argument("--loop-root", type=Path, default=Path(".taqt/loops"))
    parser.add_argument("--runs-root", type=Path, default=Path(".taqt/runs"))
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--worker-id", default="local")
    args = parser.parse_args(argv)

    task_path, task = load_task(args.task)
    task["status"] = "running"
    task["worker"] = {"id": args.worker_id, "heartbeat_at": utc_now()}
    save_task(task_path, task)

    loop_path = args.loop_root / f"{task['loop']}.yaml"
    result = run_loop(
        loop_path=loop_path,
        task_path=task_path,
        workspace=args.workspace,
        runs_root=args.runs_root,
    )

    if result["status"] == "done":
        task["status"] = "done"
        task["blocked_reason"] = None
    elif result["status"] == "human":
        task["status"] = "blocked"
        task["blocked_reason"] = "human escalation required"
    else:
        task["status"] = result["status"]
        task["blocked_reason"] = f"loop ended with status {result['status']}"
    task["phase"] = result["status"]
    task["run"] = {
        "id": Path(result["run_dir"]).name,
        "state_path": str(Path(result["run_dir"]) / "state.json"),
        "events_path": str(Path(result["run_dir"]) / "events.jsonl"),
    }
    task["worker"] = {"id": None, "heartbeat_at": None}
    save_task(task_path, task)
    print(result["run_dir"])
    return 0 if result["status"] in {"done", "human"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
