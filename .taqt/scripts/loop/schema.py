from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_document(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
    else:
        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping")
    return payload


def write_document(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def validate_loop_definition(loop: dict[str, Any]) -> None:
    if loop.get("version") != 1:
        raise ValueError("loop.version must be 1")
    if not isinstance(loop.get("id"), str) or not loop["id"]:
        raise ValueError("loop.id is required")
    steps = loop.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("loop.steps must be a non-empty list")

    seen: set[str] = set()
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"step {index} must be a mapping")
        step_id = step.get("id")
        if not isinstance(step_id, str) or not step_id:
            raise ValueError(f"step {index} id is required")
        if step_id in seen:
            raise ValueError(f"duplicate step id: {step_id}")
        seen.add(step_id)
        kind = step.get("kind")
        if kind not in {"commands", "policy", "llm", "terminal"}:
            raise ValueError(f"step {step_id} has unsupported kind: {kind}")


def validate_task(task: dict[str, Any]) -> None:
    if not isinstance(task.get("id"), str) or not task["id"]:
        raise ValueError("task.id is required")
    source = task.get("source")
    if not isinstance(source, dict) or source.get("type") != "github_issue":
        raise ValueError("task.source.type must be github_issue")
    if not source.get("repo") or not source.get("issue_number"):
        raise ValueError("task.source.repo and source.issue_number are required")
    if task.get("status") not in {"pending", "running", "blocked", "done", "failed"}:
        raise ValueError("task.status is invalid")
