from __future__ import annotations

from pathlib import Path
from typing import Any

from loop.schema import load_document, validate_task, write_document


DEFAULT_TASK_ROOT = Path(".taqt/tasks")


def task_path(task_id: str, task_root: Path = DEFAULT_TASK_ROOT) -> Path:
    return task_root / f"{task_id}.yaml"


def load_task(task_id_or_path: str, task_root: Path = DEFAULT_TASK_ROOT) -> tuple[Path, dict[str, Any]]:
    raw = Path(task_id_or_path)
    path = raw if raw.suffix in {".yaml", ".yml", ".json"} else task_path(task_id_or_path, task_root)
    task = load_document(path)
    validate_task(task)
    return path, task


def save_task(path: Path, task: dict[str, Any]) -> None:
    validate_task(task)
    write_document(path, task)


def create_issue_task(
    *,
    repo: str,
    issue_number: int,
    loop: str,
    priority: str = "normal",
    requirement: str | None = None,
    task_id: str | None = None,
    task_root: Path = DEFAULT_TASK_ROOT,
) -> tuple[Path, dict[str, Any]]:
    task_id = task_id or f"ISSUE-{issue_number}"
    task = {
        "id": task_id,
        "source": {
            "type": "github_issue",
            "repo": repo,
            "issue_number": issue_number,
        },
        "status": "pending",
        "phase": "spec",
        "priority": priority,
        "loop": loop,
        "input": {},
        "run": {
            "id": None,
            "state_path": None,
            "events_path": None,
        },
        "worker": {
            "id": None,
            "heartbeat_at": None,
        },
        "blocked_reason": None,
    }
    if requirement:
        task["input"]["requirement"] = requirement
    path = task_path(task_id, task_root)
    save_task(path, task)
    return path, task


def issue_branch(task: dict[str, Any]) -> str:
    source = task["source"]
    return f"issue-{source['issue_number']}-development-feedback-loop"


def issue_ref(task: dict[str, Any]) -> str:
    source = task["source"]
    return f"{source['repo']}#{source['issue_number']}"
