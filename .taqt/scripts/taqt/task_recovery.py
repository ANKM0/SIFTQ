import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from loop.schema import load_document, validate_task

from .task_lifecycle import complete_task
from .task_paths import DEFAULT_TASK_ROOT
from .task_repo import save_task, task_path


def recover_stale_task(
    path: Path,
    task: dict[str, Any],
    *,
    stale_minutes: int,
    now: datetime | None = None,
) -> bool:
    now = now or datetime.now(timezone.utc)
    if not is_stale_task(task, stale_minutes=stale_minutes, now=now):
        return False
    _recover_run_state(task, reason=f"stale run recovered after {stale_minutes} minutes")
    task["status"] = "pending"
    task["phase"] = "triage"
    task["blocked_reason"] = f"stale run recovered after {stale_minutes} minutes"
    task["worker"] = {"id": None, "heartbeat_at": None}
    save_task(path, task)
    return True


def is_stale_task(
    task: dict[str, Any],
    *,
    stale_minutes: int,
    now: datetime | None = None,
) -> bool:
    if task.get("status") != "running":
        return False
    timestamp = _worker_timestamp(task)
    if timestamp is None:
        return False
    now = now or datetime.now(timezone.utc)
    return now - timestamp >= timedelta(minutes=stale_minutes)


def complete_parent_if_children_done(
    parent_path: Path,
    parent: dict[str, Any],
    *,
    task_root: Path = DEFAULT_TASK_ROOT,
) -> bool:
    plan = parent.get("plan")
    slices = plan.get("slices") if isinstance(plan, dict) else None
    if not isinstance(slices, list) or not slices:
        return False
    child_ids = [
        str(slice_item.get("task_id"))
        for slice_item in slices
        if isinstance(slice_item, dict) and slice_item.get("task_id")
    ]
    if not child_ids:
        return False
    for child_id in child_ids:
        child_path = task_path(child_id, task_root)
        if not child_path.exists():
            return False
        child = load_document(child_path)
        validate_task(child)
        if child.get("status") != "done":
            return False
    complete_task(parent_path, parent, reason=None)
    return True


def _worker_timestamp(task: dict[str, Any]) -> datetime | None:
    worker = task.get("worker")
    if not isinstance(worker, dict):
        return None
    raw = worker.get("heartbeat_at") or worker.get("started_at")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


def _recover_run_state(task: dict[str, Any], *, reason: str) -> None:
    run = task.get("run")
    state_path = run.get("state_path") if isinstance(run, dict) else None
    if not isinstance(state_path, str) or not state_path:
        return
    path = Path(state_path)
    if not path.exists():
        return
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    if not isinstance(state, dict) or state.get("status") != "running":
        return
    state["status"] = "failed"
    state["blocked_reason"] = reason
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
