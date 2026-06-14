from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Iterable, Mapping, Sequence


STATUS_LABELS = (
    "sympohy:pending",
    "sympohy:running",
    "sympohy:blocked",
    "sympohy:done",
)

PHASES = ("triage", "implement", "hooks", "review", "fix", "merge")
PHASE_LABELS = tuple(f"sympohy:phase:{phase}" for phase in PHASES)
BLOCKING_REVIEW_SEVERITIES = {"critical", "high", "medium"}

COMMIT_SUBJECT_RE = re.compile(
    r"^#\d+ (feat|fix|docs|test|refactor|chore|ci|build|perf|style)"
    r"(\([a-z0-9-]+\))?!?: .+"
)


@dataclass(frozen=True)
class AcceptanceSet:
    acceptance_criteria: tuple[str, ...]
    definition_of_done: tuple[str, ...]
    source: str

    @property
    def complete(self) -> bool:
        return bool(self.acceptance_criteria and self.definition_of_done)


@dataclass(frozen=True)
class ReviewFinding:
    severity: str
    summary: str
    status: str = "open"

    @property
    def blocking(self) -> bool:
        return (
            self.status != "resolved"
            and self.severity.lower() in BLOCKING_REVIEW_SEVERITIES
        )


@dataclass(frozen=True)
class ReviewResult:
    findings: tuple[ReviewFinding, ...]
    raw: Mapping[str, object]

    @property
    def blocking_findings(self) -> tuple[ReviewFinding, ...]:
        return tuple(finding for finding in self.findings if finding.blocking)

    @property
    def approved(self) -> bool:
        return not self.blocking_findings


def validate_commit_subject(subject: str) -> bool:
    return COMMIT_SUBJECT_RE.match(subject) is not None


def is_candidate_issue(issue: Mapping[str, object]) -> bool:
    if issue.get("state", "OPEN") not in {"OPEN", "open"}:
        return False
    names = set(_label_names(issue.get("labels", [])))
    return not names.intersection(STATUS_LABELS)


def transition_labels(
    current_labels: Iterable[str],
    *,
    status: str | None = None,
    phase: str | None = None,
) -> tuple[str, ...]:
    labels = {
        label
        for label in current_labels
        if label not in STATUS_LABELS and label not in PHASE_LABELS
    }

    if status is not None:
        if status not in STATUS_LABELS:
            raise ValueError(f"unknown sympohy status label: {status}")
        labels.add(status)

    if phase is not None:
        phase_label = phase if phase.startswith("sympohy:phase:") else f"sympohy:phase:{phase}"
        if phase_label not in PHASE_LABELS:
            raise ValueError(f"unknown sympohy phase label: {phase_label}")
        labels.add(phase_label)

    return tuple(sorted(labels))


def extract_acceptance_set(body: str, comments: Sequence[Mapping[str, object]]) -> AcceptanceSet | None:
    latest: AcceptanceSet | None = _extract_from_text(body, "issue body")
    if latest is not None and not latest.complete:
        latest = None

    for index, comment in enumerate(comments, start=1):
        text = str(comment.get("body", ""))
        candidate = _extract_from_text(text, f"comment {index}")
        if candidate is not None and candidate.complete:
            latest = candidate

    return latest


def parse_review_json(source: str) -> ReviewResult:
    payload = json.loads(source)
    findings_payload = payload.get("findings", [])
    if not isinstance(findings_payload, list):
        raise ValueError("review JSON must contain findings as a list")

    findings: list[ReviewFinding] = []
    for item in findings_payload:
        if not isinstance(item, Mapping):
            raise ValueError("each review finding must be an object")
        findings.append(
            ReviewFinding(
                severity=str(item.get("severity", "")).lower(),
                summary=str(item.get("summary", "")),
                status=str(item.get("status", "open")).lower(),
            )
        )

    return ReviewResult(findings=tuple(findings), raw=payload)


def next_retry_action(attempts: int, max_attempts: int = 3) -> str:
    if attempts < 0:
        raise ValueError("attempts must be non-negative")
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    return "retry" if attempts < max_attempts else "block"


def merge_gate_allows_merge(
    *,
    final_verifier: Mapping[str, object],
    github_checks_status: str,
    review_result: ReviewResult,
) -> bool:
    recommendation = str(final_verifier.get("merge_recommendation", "")).lower()
    ac_satisfied = bool(final_verifier.get("acceptance_criteria_satisfied"))
    dod_satisfied = bool(final_verifier.get("definition_of_done_satisfied"))
    checks_passed = github_checks_status.lower() in {"pass", "passed", "success"}
    return (
        recommendation == "merge"
        and ac_satisfied
        and dod_satisfied
        and checks_passed
        and review_result.approved
    )


def _extract_from_text(text: str, source: str) -> AcceptanceSet | None:
    sections = _sections(text)
    ac = _first_section_items(sections, ("ac", "acceptance criteria", "受け入れ条件"))
    dod = _first_section_items(sections, ("dod", "definition of done", "完了の定義"))
    if not ac and not dod:
        return None
    return AcceptanceSet(
        acceptance_criteria=tuple(ac),
        definition_of_done=tuple(dod),
        source=source,
    )


def _sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        heading = _heading(raw_line)
        if heading is not None:
            if current_heading is not None:
                sections[current_heading] = current_lines
            current_heading = heading
            current_lines = []
            continue
        if current_heading is not None:
            current_lines.append(raw_line)

    if current_heading is not None:
        sections[current_heading] = current_lines
    return sections


def _heading(line: str) -> str | None:
    stripped = line.strip()
    match = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
    if match is not None:
        return _normalize_heading(match.group(1))
    if stripped.endswith(":") and stripped[:-1].lower() in {"ac", "dod"}:
        return _normalize_heading(stripped[:-1])
    return None


def _normalize_heading(heading: str) -> str:
    return re.sub(r"<!--.*?-->", "", heading).strip().lower()


def _first_section_items(sections: Mapping[str, list[str]], names: Iterable[str]) -> list[str]:
    aliases = tuple(names)
    for heading, lines in sections.items():
        if any(alias in heading for alias in aliases):
            return _checklist_items(lines)
    return []


def _checklist_items(lines: Iterable[str]) -> list[str]:
    items: list[str] = []
    for line in lines:
        match = re.match(r"^\s*[-*]\s+(?:\[[ xX]\]\s+)?(.+?)\s*$", line)
        if match is not None:
            item = match.group(1).strip()
            if item and not item.startswith("<!--"):
                items.append(item)
    return items


def _label_names(labels: object) -> list[str]:
    if not isinstance(labels, list):
        return []
    names: list[str] = []
    for label in labels:
        if isinstance(label, str):
            names.append(label)
        elif isinstance(label, Mapping):
            name = label.get("name")
            if isinstance(name, str):
                names.append(name)
    return names
