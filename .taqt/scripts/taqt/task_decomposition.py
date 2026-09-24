from pathlib import Path
from typing import Any

from .task_paths import DECOMPOSITION_SECTION_GROUPS, DEFAULT_SLICE_MINUTES
from .task_readiness import _issue_title, _readiness_sections, _section_bullets


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


def _slice_issue_body(*, title: str, source_section: str) -> str:
    return "\n".join(
        [
            "## Slice",
            "- Source section: " + source_section,
            "- Target: " + title,
            "",
            "## AC",
            "- Complete only this 5-minute slice: " + title,
            "",
            "## DoD",
            "- The slice result is implemented or explicitly reported as blocked.",
            "- The smallest meaningful validation for this slice is run or recorded.",
        ]
    )
