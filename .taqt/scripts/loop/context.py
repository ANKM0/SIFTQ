from __future__ import annotations

from pathlib import Path
from typing import Any


def build_context(
    *,
    task: dict[str, Any],
    step: dict[str, Any],
    events: list[dict[str, Any]],
    workspace: Path,
    max_file_bytes: int = 20000,
) -> dict[str, Any]:
    inputs = task.get("input") if isinstance(task.get("input"), dict) else {}
    files: dict[str, str] = {}
    for key, value in inputs.items():
        if not isinstance(value, str):
            continue
        path = workspace / value
        if path.is_file():
            files[key] = path.read_text(encoding="utf-8")[:max_file_bytes]
    return {
        "task": task,
        "step": step,
        "recent_events": events[-10:],
        "files": files,
    }
