from pathlib import Path
from typing import Any

from .task_repo import save_task


def triage_task(path: Path, task: dict[str, Any], reason: str) -> None:
    task["status"] = "pending"
    task["phase"] = "triage"
    task["blocked_reason"] = reason
    task["worker"] = {"id": None, "heartbeat_at": None}
    save_task(path, task)


def block_task(path: Path, task: dict[str, Any], reason: str) -> None:
    task["status"] = "blocked"
    task["phase"] = "human"
    task["blocked_reason"] = reason
    task["worker"] = {"id": None, "heartbeat_at": None}
    save_task(path, task)


def complete_task(path: Path, task: dict[str, Any], *, reason: str | None = None) -> None:
    task["status"] = "done"
    task["phase"] = "done"
    task["blocked_reason"] = reason
    task["worker"] = {"id": None, "heartbeat_at": None}
    save_task(path, task)
