import re
from pathlib import Path
from typing import Any

from loop.schema import load_document, validate_task, write_document


DEFAULT_TASK_ROOT = Path(".taqt/tasks")
PRIORITY_ORDER = {"high": 0, "normal": 1, "low": 2}


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


def list_tasks(task_root: Path = DEFAULT_TASK_ROOT) -> list[tuple[Path, dict[str, Any]]]:
    if not task_root.exists():
        return []
    tasks: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(task_root.glob("*.yaml")):
        task = load_document(path)
        validate_task(task)
        tasks.append((path, task))
    return tasks


def next_pending_task(task_root: Path = DEFAULT_TASK_ROOT) -> tuple[Path, dict[str, Any]] | None:
    pending = [
        (path, task)
        for path, task in list_tasks(task_root)
        if task.get("status") == "pending"
    ]
    if not pending:
        return None
    return sorted(
        pending,
        key=lambda item: (
            PRIORITY_ORDER.get(str(item[1].get("priority")), PRIORITY_ORDER["normal"]),
            item[0].name,
        ),
    )[0]


def create_issue_task(
    *,
    repo: str,
    issue_number: int,
    loop: str,
    priority: str = "normal",
    requirement: str | None = None,
    branch_summary: str | None = None,
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
    if branch_summary is not None:
        task["branch_summary"] = branch_summary
    if requirement:
        task["input"]["requirement"] = requirement
    path = task_path(task_id, task_root)
    save_task(path, task)
    return path, task


def upsert_issue_task(
    *,
    repo: str,
    issue_number: int,
    loop: str,
    priority: str = "normal",
    requirement: str | None = None,
    branch_summary: str | None = None,
    issue_title: str | None = None,
    issue_body: str | None = None,
    issue_labels: list[str] | None = None,
    task_root: Path = DEFAULT_TASK_ROOT,
) -> tuple[Path, dict[str, Any], bool]:
    path = task_path(f"ISSUE-{issue_number}", task_root)
    if not path.exists():
        created_path, created = create_issue_task(
            repo=repo,
            issue_number=issue_number,
            loop=loop,
            priority=priority,
            requirement=requirement,
            branch_summary=branch_summary or issue_title,
            task_root=task_root,
        )
        _merge_issue_metadata(
            created,
            title=issue_title,
            body=issue_body,
            labels=issue_labels,
        )
        save_task(created_path, created)
        return created_path, created, True

    task = load_document(path)
    validate_task(task)
    task["source"] = {
        "type": "github_issue",
        "repo": repo,
        "issue_number": issue_number,
    }
    task["loop"] = loop
    task["priority"] = priority
    if requirement:
        task.setdefault("input", {})["requirement"] = requirement
    if (branch_summary or issue_title) and not task.get("branch_summary"):
        task["branch_summary"] = branch_summary or issue_title
    _merge_issue_metadata(
        task,
        title=issue_title,
        body=issue_body,
        labels=issue_labels,
    )
    save_task(path, task)
    return path, task, False


def issue_branch(task: dict[str, Any]) -> str:
    source = task["source"]
    return f"dev/#{source['issue_number']}_{branch_purpose(task)}"


def branch_purpose(task: dict[str, Any]) -> str:
    purpose = str(task.get("branch_summary") or task.get("loop") or "development")
    normalized = re.sub(r"[^a-z0-9_]+", "_", purpose.lower()).strip("_")
    return normalized or "development"


def issue_ref(task: dict[str, Any]) -> str:
    source = task["source"]
    return f"{source['repo']}#{source['issue_number']}"


def _merge_issue_metadata(
    task: dict[str, Any],
    *,
    title: str | None,
    body: str | None,
    labels: list[str] | None,
) -> None:
    issue: dict[str, Any] = {}
    if title is not None:
        issue["title"] = title
    if body is not None:
        issue["body"] = body
    if labels is not None:
        issue["labels"] = labels
    if issue:
        task.setdefault("input", {})["issue"] = issue
