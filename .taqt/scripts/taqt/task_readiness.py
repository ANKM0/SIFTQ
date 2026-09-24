import re
from pathlib import Path
from typing import Any

from .task_paths import (
    BUG_REQUIRED_SECTIONS,
    BUG_WARNING_SECTIONS,
    FEATURE_REQUIRED_SECTIONS,
    RESEARCH_REQUIRED_SECTIONS,
)


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
