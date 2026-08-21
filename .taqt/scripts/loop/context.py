import json
import subprocess
from pathlib import Path
from typing import Any


MAX_RECENT_EVENTS = 10
MAX_EVENT_CHARS = 12000
MAX_EVENT_STRING_CHARS = 2000


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
        "recent_events": [_compact_event(event) for event in events[-MAX_RECENT_EVENTS:]],
        "files": files,
        "repository": _repository_context(workspace),
        "artifacts": _artifact_context(workspace),
    }


def _repository_context(workspace: Path) -> dict[str, str]:
    return {
        "branch": _run_git(["git", "branch", "--show-current"], workspace, limit=200),
        "status": _run_git(["git", "status", "--short"], workspace, limit=4000),
        "diff_stat": _run_git(["git", "diff", "--stat"], workspace, limit=4000),
        "diff_name_only": _run_git(["git", "diff", "--name-only"], workspace, limit=4000),
    }


def _artifact_context(workspace: Path) -> list[str]:
    artifacts = workspace / ".taqt" / "runs"
    if not artifacts.exists():
        return []
    paths = [
        path.relative_to(workspace).as_posix()
        for path in artifacts.glob("**/*")
        if path.is_file() and path.name in {"state.json", "events.jsonl"}
    ]
    return sorted(paths)[-20:]


def _run_git(command: list[str], cwd: Path, *, limit: int) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return completed.stderr[:limit]
    return completed.stdout[:limit]


def _compact_event(event: dict[str, Any]) -> dict[str, Any]:
    compacted = _truncate_strings(event)
    serialized = json.dumps(compacted, ensure_ascii=False, sort_keys=True)
    if len(serialized) <= MAX_EVENT_CHARS:
        return compacted
    return {
        "type": event.get("type"),
        "step": event.get("step"),
        "created_at": event.get("created_at"),
        "summary": serialized[:MAX_EVENT_CHARS] + "…",
    }


def _truncate_strings(value: Any) -> Any:
    if isinstance(value, str):
        return value[:MAX_EVENT_STRING_CHARS] + ("…" if len(value) > MAX_EVENT_STRING_CHARS else "")
    if isinstance(value, list):
        return [_truncate_strings(item) for item in value]
    if isinstance(value, dict):
        return {key: _truncate_strings(item) for key, item in value.items()}
    return value
