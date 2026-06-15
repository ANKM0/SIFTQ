from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Callable, Iterable, Mapping, Sequence


STATUS_LABELS = (
    "sympohy:pending",
    "sympohy:running",
    "sympohy:blocked",
    "sympohy:done",
)

PHASES = ("triage", "implement", "hooks", "review", "fix", "finalize")
PHASE_LABELS = tuple(f"sympohy:phase:{phase}" for phase in PHASES)
PHASE_ALIASES = {"merge": "finalize"}
LEGACY_PHASE_LABELS = ("sympohy:phase:merge",)


def _normalize_phase_label(phase: str) -> str:
    normalized = phase.removeprefix("sympohy:phase:")
    normalized = PHASE_ALIASES.get(normalized, normalized)
    return f"sympohy:phase:{normalized}"
BLOCKING_REVIEW_SEVERITIES = {"critical", "high", "medium"}
FINAL_VERIFIER_FINDING_KINDS = {
    "acceptance_criteria",
    "definition_of_done",
    "verification",
    "reviewability",
    "other",
}
DEFAULT_STALE_STATUS_AFTER_MINUTES = 30
# Legacy task label prefixes are intentionally supported to migrate historical issues
# from prior runners; they are expected to be removed from all active flow over
# time after migration.
LEGACY_TASK_LABEL_PREFIXES = ("ai:", "takt:", "taqt:")
LEGACY_DONE_LABELS = {
    "ai:done",
    "ai:complete",
    "ai:completed",
    "ai:merged",
    "takt:done",
    "takt:complete",
    "taqt:done",
    "taqt:complete",
}
LEGACY_BLOCKED_LABELS = {
    "ai:blocked",
    "ai:needs-human",
    "ai:needs-input",
    "takt:blocked",
    "taqt:blocked",
}
LEGACY_REVIEW_LABELS = {"ai:review", "ai:needs-review", "takt:review", "taqt:review"}
LEGACY_FIX_LABELS = {"ai:fix", "ai:needs-fix", "takt:fix", "taqt:fix"}
LEGACY_HOOK_LABELS = {"ai:hooks", "ai:ci", "ai:test", "takt:hooks", "taqt:hooks"}
LEGACY_RUNNING_LABELS = {
    "ai:running",
    "ai:implementing",
    "ai:in-progress",
    "takt:running",
    "takt:in-progress",
    "taqt:running",
    "taqt:in-progress",
}

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
class RunningIssueInspection:
    phase: str | None
    stale: bool
    reason: str | None
    state_path: Path | None
    state: Mapping[str, object] | None = None


@dataclass(frozen=True)
class ResumePoint:
    name: str
    phase: str | None
    terminal: bool = False


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


@dataclass(frozen=True)
class FinalVerifierFinding:
    kind: str
    summary: str
    evidence: str
    suggested_fix: str


def validate_commit_subject(subject: str) -> bool:
    return COMMIT_SUBJECT_RE.match(subject) is not None


def is_candidate_issue(
    issue: Mapping[str, object],
    *,
    run_log_root: Path | None = None,
    now: datetime | None = None,
    process_alive: Callable[[int], bool] | None = None,
    stale_status_after_minutes: int = DEFAULT_STALE_STATUS_AFTER_MINUTES,
) -> bool:
    if issue.get("state", "OPEN") not in {"OPEN", "open"}:
        return False
    names = set(_label_names(issue.get("labels", [])))
    if not names.intersection(STATUS_LABELS):
        return True
    if not names.intersection({"sympohy:pending", "sympohy:running"}):
        return False
    return inspect_running_issue(
        issue,
        run_log_root=run_log_root or Path(".sympohy/runs"),
        now=now,
        process_alive=process_alive,
        stale_status_after_minutes=stale_status_after_minutes,
    ).stale


def inspect_running_issue(
    issue: Mapping[str, object],
    *,
    run_log_root: Path,
    now: datetime | None = None,
    process_alive: Callable[[int], bool] | None = None,
    stale_status_after_minutes: int = DEFAULT_STALE_STATUS_AFTER_MINUTES,
) -> RunningIssueInspection:
    names = set(_label_names(issue.get("labels", [])))
    label_phase = _phase_from_labels(names)
    try:
        number = int(issue["number"])
    except (KeyError, TypeError, ValueError):
        return RunningIssueInspection(
            phase=label_phase,
            stale=True,
            reason="missing issue number",
            state_path=None,
        )

    state_path = run_log_root / f"issue-{number}" / "state.json"
    state = read_run_state(state_path)
    if state is None:
        reason = "corrupt state" if state_path.exists() else "missing state"
        return RunningIssueInspection(
            phase=label_phase,
            stale=True,
            reason=reason,
            state_path=state_path,
            state=None,
        )

    phase = phase_from_state(state) or label_phase
    state_error = _state_identity_error(state, number)
    if state_error is not None:
        return RunningIssueInspection(
            phase=phase,
            stale=True,
            reason=state_error,
            state_path=state_path,
            state=state,
        )

    if phase is None:
        return RunningIssueInspection(
            phase=None,
            stale=True,
            reason="missing phase",
            state_path=state_path,
            state=state,
        )

    pid = _state_pid(state)
    if pid is None:
        return RunningIssueInspection(
            phase=phase,
            stale=True,
            reason="missing pid",
            state_path=state_path,
            state=state,
        )
    alive = process_alive or _process_alive
    if not alive(pid):
        return RunningIssueInspection(
            phase=phase,
            stale=True,
            reason="dead pid",
            state_path=state_path,
            state=state,
        )

    heartbeat = _state_heartbeat(state)
    if heartbeat is None:
        return RunningIssueInspection(
            phase=phase,
            stale=True,
            reason="missing heartbeat",
            state_path=state_path,
            state=state,
        )
    current_time = _normalize_datetime(now or datetime.now(timezone.utc))
    stale_after_seconds = stale_status_after_minutes * 60
    if (current_time - heartbeat).total_seconds() > stale_after_seconds:
        return RunningIssueInspection(
            phase=phase,
            stale=True,
            reason="stale heartbeat",
            state_path=state_path,
            state=state,
        )

    return RunningIssueInspection(
        phase=phase,
        stale=False,
        reason=None,
        state_path=state_path,
        state=state,
    )


def transition_labels(
    current_labels: Iterable[str],
    *,
    status: str | None = None,
    phase: str | None = None,
) -> tuple[str, ...]:
    labels = {
        label
        for label in current_labels
        if label not in STATUS_LABELS
        and label not in PHASE_LABELS
        and label not in LEGACY_PHASE_LABELS
    }

    if status is not None:
        if status not in STATUS_LABELS:
            raise ValueError(f"unknown sympohy status label: {status}")
        labels.add(status)

    if phase is not None:
        phase_label = _normalize_phase_label(phase)
        if phase_label not in PHASE_LABELS:
            raise ValueError(f"unknown sympohy phase label: {phase_label}")
        labels.add(phase_label)

    return tuple(sorted(labels))


def migrate_task_labels(
    current_labels: Iterable[str],
    *,
    issue_state: str = "OPEN",
) -> tuple[str, ...]:
    labels = tuple(current_labels)
    names = set(labels)
    preserved = [
        label
        for label in labels
        if label not in STATUS_LABELS
        and label not in PHASE_LABELS
        and not _is_legacy_task_label(label)
    ]
    status = _single_label(names, STATUS_LABELS) or _legacy_status(names, issue_state)
    phase = _single_label(names, PHASE_LABELS) or _legacy_phase(names, status)
    return transition_labels(preserved, status=status, phase=phase)


def resolve_resume_point(
    labels: object,
    *,
    state: Mapping[str, object] | None = None,
) -> ResumePoint:
    names = set(_label_names(labels))
    phase = phase_from_state(state) if state is not None else None
    if phase is None:
        phase = _phase_from_labels(names)
    status = state.get("status") if state is not None else None

    if state is not None:
        if status == "done":
            return ResumePoint(name="completed", phase=phase, terminal=True)
        if status == "blocked":
            return ResumePoint(name="blocked", phase=phase, terminal=True)
    else:
        if "sympohy:done" in names:
            return ResumePoint(name="completed", phase=phase, terminal=True)
        if "sympohy:blocked" in names:
            return ResumePoint(name="blocked", phase=phase, terminal=True)

    if phase in {None, "triage"}:
        return ResumePoint(name="planning", phase=phase)
    if phase in {"implement", "hooks", "review", "fix", "finalize"}:
        return ResumePoint(name=phase, phase=phase)

    return ResumePoint(name="planning", phase=phase)


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
    if isinstance(payload, list):
        findings_payload = payload
    elif isinstance(payload, Mapping):
        findings_payload = payload.get("findings", [])
    else:
        raise ValueError("review JSON must be an object or findings list")
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


def parse_final_verifier_block_findings(
    final_verifier: Mapping[str, object],
) -> tuple[FinalVerifierFinding, ...]:
    if "findings" not in final_verifier:
        raise ValueError("final verifier block response must include findings")
    findings_payload = final_verifier["findings"]
    if not isinstance(findings_payload, list):
        raise ValueError("final verifier findings must be a list")
    if not findings_payload:
        raise ValueError("final verifier block response must include non-empty findings")

    findings: list[FinalVerifierFinding] = []
    for index, item in enumerate(findings_payload, start=1):
        if not isinstance(item, Mapping):
            raise ValueError(f"final verifier finding {index} must be an object")
        fields: dict[str, str] = {}
        for field in ("kind", "summary", "evidence", "suggested_fix"):
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"final verifier finding {index} must include non-empty {field}"
                )
            fields[field] = value.strip()
        if fields["kind"] not in FINAL_VERIFIER_FINDING_KINDS:
            raise ValueError(
                f"final verifier finding {index} has unknown kind: {fields['kind']}"
            )
        findings.append(FinalVerifierFinding(**fields))

    return tuple(findings)


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
    in_fence = False

    for raw_line in text.splitlines():
        if raw_line.strip().startswith("```"):
            in_fence = not in_fence
            if current_heading is not None:
                current_lines.append(raw_line)
            continue
        if in_fence:
            if current_heading is not None:
                current_lines.append(raw_line)
            continue

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
            items = _checklist_items(lines)
            if items:
                return items
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


def _phase_from_labels(labels: Iterable[str]) -> str | None:
    phases = {
        PHASE_ALIASES.get(
            label.removeprefix("sympohy:phase:"), label.removeprefix("sympohy:phase:")
        )
        for label in labels
        if label.startswith("sympohy:phase:")
    }
    if len(phases) != 1:
        return None
    phase = next(iter(phases))
    if f"sympohy:phase:{phase}" in PHASE_LABELS:
        return phase
    return None


def _is_legacy_task_label(label: str) -> bool:
    normalized = label.lower()
    return any(normalized.startswith(prefix) for prefix in LEGACY_TASK_LABEL_PREFIXES)


def _single_label(labels: set[str], candidates: Sequence[str]) -> str | None:
    matches = [label for label in candidates if label in labels]
    if len(matches) == 1:
        return matches[0]
    return None


def _legacy_status(labels: set[str], issue_state: str) -> str:
    normalized = {label.lower() for label in labels}
    if issue_state.upper() in {"CLOSED", "CLOSE"} or normalized.intersection(
        LEGACY_DONE_LABELS
    ):
        return "sympohy:done"
    if normalized.intersection(LEGACY_BLOCKED_LABELS):
        return "sympohy:blocked"
    if normalized.intersection(
        LEGACY_REVIEW_LABELS | LEGACY_FIX_LABELS | LEGACY_HOOK_LABELS | LEGACY_RUNNING_LABELS
    ):
        return "sympohy:running"
    return "sympohy:pending"


def _legacy_phase(labels: set[str], status: str) -> str:
    normalized = {label.lower() for label in labels}
    if status == "sympohy:done":
        return "finalize"
    if normalized.intersection(LEGACY_FIX_LABELS):
        return "fix"
    if normalized.intersection(LEGACY_REVIEW_LABELS):
        return "review"
    if normalized.intersection(LEGACY_HOOK_LABELS):
        return "hooks"
    if normalized.intersection(LEGACY_RUNNING_LABELS):
        return "implement"
    if status == "sympohy:blocked":
        return "triage"
    return "triage"


def read_run_state(path: Path) -> Mapping[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, Mapping):
        return None
    return payload


def phase_from_state(state: Mapping[str, object] | None) -> str | None:
    if state is None:
        return None
    phase = state.get("phase")
    if isinstance(phase, str) and phase in PHASES:
        return phase
    if isinstance(phase, str):
        return PHASE_ALIASES.get(phase)
    return None


def _state_pid(state: Mapping[str, object]) -> int | None:
    value = state.get("pid")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        pid = value
    elif isinstance(value, str):
        try:
            pid = int(value)
        except ValueError:
            return None
    else:
        return None
    return pid if pid > 0 else None


def _state_identity_error(state: Mapping[str, object], issue_number: int) -> str | None:
    state_issue = state.get("issue")
    try:
        if int(state_issue) != issue_number:
            return "invalid state"
    except (TypeError, ValueError):
        return "invalid state"

    run_id = state.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        return "invalid state"

    state_lock = state.get("lock")
    if isinstance(state_lock, Mapping):
        lock_run_id = state_lock.get("run_id")
        if lock_run_id not in {None, run_id}:
            return "invalid state"

    return None


def _state_heartbeat(state: Mapping[str, object]) -> datetime | None:
    value = state.get("heartbeat")
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        heartbeat = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _normalize_datetime(heartbeat)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _label_names(labels: object) -> list[str]:
    if not isinstance(labels, (list, tuple)):
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
