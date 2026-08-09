import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from loop.schema import load_document, validate_task, write_document


DEFAULT_TASK_ROOT = Path(".taqt/tasks")
DEFAULT_SLICE_MINUTES = 5
PRIORITY_ORDER = {"high": 0, "normal": 1, "low": 2}
FEATURE_REQUIRED_SECTIONS = {
    "AC": ("ac", "acceptance criteria", "受け入れ条件", "受入条件"),
    "DoD": ("dod", "definition of done", "完了の定義"),
}
RESEARCH_REQUIRED_SECTIONS = {
    "調べたいこと": ("調べたいこと", "research questions"),
    "完了条件": ("完了条件", "completion criteria", "done criteria"),
}
BUG_REQUIRED_SECTIONS = {
    "概要": ("概要", "summary"),
}
BUG_WARNING_SECTIONS = {
    "再現手順": ("再現手順", "steps to reproduce", "reproduction"),
}
DECOMPOSITION_SECTION_GROUPS = (
    ("AC", FEATURE_REQUIRED_SECTIONS["AC"]),
    ("task", ("task", "tasks", "todo", "やること")),
    ("調べたいこと", RESEARCH_REQUIRED_SECTIONS["調べたいこと"]),
    ("再現手順", BUG_WARNING_SECTIONS["再現手順"]),
    ("概要", BUG_REQUIRED_SECTIONS["概要"]),
)


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
        if task.get("status") == "pending" and task.get("phase") != "decomposed"
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


def decomposition_errors(
    task: dict[str, Any],
    *,
    workspace: Path = Path("."),
    max_minutes: int = DEFAULT_SLICE_MINUTES,
) -> list[str]:
    if task.get("slice"):
        return []
    plan = task.get("plan")
    if isinstance(plan, dict) and isinstance(plan.get("slices"), list) and plan["slices"]:
        child_ids = [
            str(slice_item.get("task_id"))
            for slice_item in plan["slices"]
            if isinstance(slice_item, dict) and slice_item.get("task_id")
        ]
        if task.get("phase") == "decomposed":
            suffix = f": {', '.join(child_ids)}" if child_ids else ""
            return [f"task is decomposed; run child slice tasks{suffix}"]
        return []
    slices = decompose_issue_body(task, workspace=workspace, max_minutes=max_minutes)
    if len(slices) <= 1:
        return []
    return [f"task requires decomposition into {len(slices)} slices capped at {max_minutes} minutes"]


def decompose_issue_body(
    task: dict[str, Any],
    *,
    workspace: Path = Path("."),
    max_minutes: int = DEFAULT_SLICE_MINUTES,
) -> list[dict[str, Any]]:
    sections = _readiness_sections(task, workspace=workspace)
    for source_section, headings in DECOMPOSITION_SECTION_GROUPS:
        items = _section_bullets(sections, headings)
        if items:
            return [
                {
                    "title": item,
                    "source_section": source_section,
                    "estimate_minutes": max_minutes,
                }
                for item in items
            ]

    title = _issue_title(task) or str(task.get("id"))
    return [
        {
            "title": title,
            "source_section": "issue title",
            "estimate_minutes": max_minutes,
        }
    ]


def slice_task_id(parent_task: dict[str, Any], index: int) -> str:
    return f"{parent_task['id']}-{index:02d}"


def build_slice_task(
    parent_task: dict[str, Any],
    slice_item: dict[str, Any],
    *,
    index: int,
    total: int,
) -> dict[str, Any]:
    title = str(slice_item["title"])
    child_id = slice_task_id(parent_task, index)
    parent_input = parent_task.get("input") if isinstance(parent_task.get("input"), dict) else {}
    parent_issue = parent_input.get("issue") if isinstance(parent_input.get("issue"), dict) else {}
    parent_title = str(parent_issue.get("title") or parent_task.get("id"))
    source = dict(parent_task["source"])
    source["parent_task"] = parent_task["id"]
    return {
        "id": child_id,
        "source": source,
        "status": "pending",
        "phase": "spec",
        "priority": parent_task.get("priority", "normal"),
        "loop": parent_task["loop"],
        "input": {
            "issue": {
                "title": f"{parent_title} / slice {index:02d}: {title}",
                "body": _slice_issue_body(title=title, source_section=str(slice_item["source_section"])),
                "labels": parent_issue.get("labels", []),
            },
            "parent_issue": parent_issue,
        },
        "slice": {
            "parent_task": parent_task["id"],
            "index": index,
            "total": total,
            "title": title,
            "source_section": slice_item["source_section"],
            "estimate_minutes": slice_item["estimate_minutes"],
        },
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
        "branch_summary": f"slice_{index:02d}",
    }


def readiness_errors(task: dict[str, Any], *, workspace: Path = Path(".")) -> list[str]:
    sections = _readiness_sections(task, workspace=workspace)
    if _looks_like_research(sections):
        return _missing_sections(sections, RESEARCH_REQUIRED_SECTIONS)
    if _looks_like_bug(sections):
        return []
    return _missing_sections(sections, FEATURE_REQUIRED_SECTIONS)


def readiness_warnings(task: dict[str, Any], *, workspace: Path = Path(".")) -> list[str]:
    sections = _readiness_sections(task, workspace=workspace)
    if _looks_like_bug(sections):
        return [
            *_missing_sections(sections, BUG_REQUIRED_SECTIONS),
            *_missing_sections(sections, BUG_WARNING_SECTIONS),
        ]
    return []


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


def _readiness_text(task: dict[str, Any], *, workspace: Path) -> str:
    inputs = task.get("input") if isinstance(task.get("input"), dict) else {}
    chunks: list[str] = []
    issue = inputs.get("issue")
    if isinstance(issue, dict):
        for key in ("title", "body"):
            value = issue.get(key)
            if isinstance(value, str):
                chunks.append(value)
    requirement = inputs.get("requirement")
    if isinstance(requirement, str):
        path = workspace / requirement
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def _readiness_sections(task: dict[str, Any], *, workspace: Path) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = ""
    for line in _readiness_text(task, workspace=workspace).splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip().lower()
            current = heading
            sections.setdefault(current, [])
            continue
        if current:
            sections.setdefault(current, []).append(line)
    return sections


def _section_bullets(sections: dict[str, list[str]], headings: tuple[str, ...]) -> list[str]:
    bullets: list[str] = []
    for heading, lines in sections.items():
        if not _matches_heading(heading, headings):
            continue
        for line in lines:
            bullet = _parse_bullet(line)
            if bullet:
                bullets.append(bullet)
    return bullets


def _looks_like_research(sections: dict[str, list[str]]) -> bool:
    return _has_heading(sections, ("調べたいこと", "research questions")) or _has_heading(
        sections,
        RESEARCH_REQUIRED_SECTIONS["完了条件"],
    )


def _looks_like_bug(sections: dict[str, list[str]]) -> bool:
    return _has_heading(sections, BUG_WARNING_SECTIONS["再現手順"])


def _missing_sections(sections: dict[str, list[str]], required: dict[str, tuple[str, ...]]) -> list[str]:
    errors: list[str] = []
    for name, headings in required.items():
        if not _section_has_content(sections, headings):
            errors.append(f"missing issue section: {name}")
    return errors


def _has_heading(sections: dict[str, list[str]], headings: tuple[str, ...]) -> bool:
    return any(_matches_heading(candidate, headings) for candidate in sections)


def _section_has_content(sections: dict[str, list[str]], headings: tuple[str, ...]) -> bool:
    for heading, lines in sections.items():
        if _matches_heading(heading, headings) and _meaningful_lines(lines):
            return True
    return False


def _matches_heading(heading: str, patterns: tuple[str, ...]) -> bool:
    normalized = heading.strip().lower()
    return any(normalized == pattern or normalized.startswith(f"{pattern} ") for pattern in patterns)


def _meaningful_lines(lines: list[str]) -> list[str]:
    meaningful: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--"):
            continue
        if stripped in {"-", "- [ ]", "- []"}:
            continue
        meaningful.append(stripped)
    return meaningful


def _parse_bullet(line: str) -> str | None:
    stripped = line.strip()
    match = re.match(r"^[-*]\s+(?:\[[ xX]\]\s*)?(?P<text>.+)$", stripped)
    if not match:
        return None
    text = match.group("text").strip()
    if not text or text in {"-", "[]", "[ ]"}:
        return None
    return text


def _issue_title(task: dict[str, Any]) -> str | None:
    inputs = task.get("input") if isinstance(task.get("input"), dict) else {}
    issue = inputs.get("issue")
    if isinstance(issue, dict) and isinstance(issue.get("title"), str):
        return issue["title"]
    return None


def _slice_issue_body(*, title: str, source_section: str) -> str:
    return "\n".join(
        [
            f"## Slice",
            f"- Source section: {source_section}",
            f"- Target: {title}",
            "",
            "## AC",
            f"- Complete only this 5-minute slice: {title}",
            "",
            "## DoD",
            "- The slice result is implemented or explicitly reported as blocked.",
            "- The smallest meaningful validation for this slice is run or recorded.",
        ]
    )


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
