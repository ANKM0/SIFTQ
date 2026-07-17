from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import signal
import subprocess
import sys
from tempfile import NamedTemporaryFile
import time
import uuid
from typing import Callable, Iterable, Mapping, Sequence

from .config import SympohyConfig
from .core import (
    AcceptanceSet,
    FinalVerifierFinding,
    PHASE_ALIASES,
    ReviewFinding,
    extract_acceptance_set,
    inspect_running_issue,
    merge_gate_allows_merge,
    next_retry_action,
    phase_from_state,
    parse_final_verifier_block_findings,
    parse_review_json,
    read_run_state,
    resolve_resume_point,
    validate_commit_subject,
)
from .github import Issue, comment, fetch_issue, list_candidate_issues, set_issue_state


HEARTBEAT_INTERVAL_SECONDS = 30
DOCUMENT_ARTIFACT_GATE_MAX_ATTEMPTS = 3
LOGICAL_STEP_COMMIT_RE = re.compile(
    r"^#(?P<issue>\d+) feat\(sympohy\): implement logical step (?P<step>\d+)$"
)
FINAL_VERIFIER_PROMPT = (
    "Act as final verifier. Return a single JSON object with status set to "
    '"pass", "retry", or "block"; boolean '
    "acceptance_criteria_satisfied, boolean definition_of_done_satisfied, "
    'merge_recommendation set to "merge" or "block", and findings as an array. '
    'Use status "pass" only when merge_recommendation is "merge". Use status '
    '"retry" when findings can be fixed automatically. Use status "block" '
    "when manual intervention is required. When merge_recommendation is "
    '"merge", findings must be an empty array. When merge_recommendation is '
    '"block", findings must be a non-empty array of objects for automated '
    "fixing or manual review. Each finding must include string fields "
    "kind, summary, evidence, and suggested_fix. kind must be one of "
    "acceptance_criteria, definition_of_done, verification, reviewability, "
    "other. summary names the unmet requirement, evidence cites the observed "
    "failure, and suggested_fix gives concrete implementation guidance."
)


class _RunLockedError(RuntimeError):
    pass


class _ExistingRunError(RuntimeError):
    pass


class _UnsafeRecoveryError(RuntimeError):
    pass


class _AmbiguousPullRequestError(RuntimeError):
    pass


class _PullRequestMetadataError(RuntimeError):
    pass


class _RunInterrupted(RuntimeError):
    pass


@dataclass(frozen=True)
class _ImplementationRecovery:
    committed_logical_steps: int
    worktree_logical_step: int | None = None
    worktree_clean: bool = True
    unsafe_reason: str | None = None

    def next_logical_step(self, total_steps: int) -> int | None:
        if self.committed_logical_steps >= total_steps:
            return None
        return self.committed_logical_steps + 1

    def implementation_complete(self, total_steps: int) -> bool:
        return self.next_logical_step(total_steps) is None

    def resume_action(self, total_steps: int) -> str:
        if self.unsafe_reason is not None:
            return "block_unsafe_resume"
        if self.implementation_complete(total_steps):
            return "push_pr"
        if self.worktree_logical_step is not None:
            return "reuse_worktree_changes"
        return "implement_next_step"

    def should_reuse_worktree(self, index: int) -> bool:
        return self.worktree_logical_step == index


@dataclass(frozen=True)
class _PullRequestMergeability:
    number: str
    base_ref: str
    head_ref: str
    merge_state_status: str
    mergeable: str

    def is_conflicted(self) -> bool:
        return self.merge_state_status == "DIRTY" or self.mergeable == "CONFLICTING"

    def conflict_summary(self) -> str:
        details = [f"mergeStateStatus={self.merge_state_status}"]
        if self.mergeable:
            details.append(f"mergeable={self.mergeable}")
        return "GitHub reports " + ", ".join(details) + "."


class _RunEventStream:
    def __init__(
        self,
        *,
        issue_number: int,
        log_dir: Path,
        run_id: str,
        clock: Callable[[], datetime],
    ) -> None:
        self.issue_number = issue_number
        self.log_dir = log_dir
        self.run_id = run_id
        self._clock = clock
        self._next_event_index = 1

    @property
    def path(self) -> Path:
        return self.log_dir / "events.jsonl"

    def append(
        self,
        *,
        phase: str | None,
        event_type: str,
        status: str,
        summary: str,
        attempt: int | None = None,
        duration: float | int | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_id": self.run_id,
            "event_id": f"{self.run_id}-{self._next_event_index:06d}",
            "issue": self.issue_number,
            "phase": phase,
            "event_type": event_type,
            "status": status,
            "attempt": attempt,
            "duration": duration,
            "summary": summary,
            "metadata": dict(metadata or {}),
            "timestamp": _isoformat_utc(self._clock()),
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        self._next_event_index += 1
        return payload


class _RunStateWriter:
    def __init__(
        self,
        *,
        issue_number: int,
        log_dir: Path,
        base_branch: str | None = None,
        worktree: Path | None = None,
        branch: str | None = None,
        plan_path: Path | None = None,
        run_id: str | None = None,
        lock_path: Path | None = None,
        refresh_lock: bool = False,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.issue_number = issue_number
        self.log_dir = log_dir
        self.run_id = run_id or _new_run_id()
        self.lock_path = lock_path or (log_dir / "run.lock")
        self.refresh_lock = refresh_lock
        self.base_branch = base_branch
        self.worktree = worktree
        self.branch = branch
        self.plan_path = plan_path
        self.phase: str | None = None
        self.status = "running"
        self.last_known_progress: Mapping[str, object] = {}
        self.last_recovery: Mapping[str, object] | None = None
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._event_stream = _RunEventStream(
            issue_number=issue_number,
            log_dir=log_dir,
            run_id=self.run_id,
            clock=self._clock,
        )

    @property
    def state_path(self) -> Path:
        return self.log_dir / "state.json"

    def write(
        self,
        *,
        phase: str | None = None,
        status: str | None = None,
        worktree: Path | None = None,
        branch: str | None = None,
        plan_path: Path | None = None,
        progress: Mapping[str, object] | None = None,
    ) -> None:
        if phase is not None:
            self.phase = phase
        if status is not None:
            self.status = status
        if worktree is not None:
            self.worktree = worktree
        if branch is not None:
            self.branch = branch
        if plan_path is not None:
            self.plan_path = plan_path
        if progress is not None:
            self.last_known_progress = progress

        self.log_dir.mkdir(parents=True, exist_ok=True)
        heartbeat = _isoformat_utc(self._clock())
        if self.refresh_lock:
            _refresh_lock_metadata(
                self.lock_path,
                run_id=self.run_id,
                issue_number=self.issue_number,
                phase=self.phase,
                heartbeat=heartbeat,
            )

        payload = {
            "run_id": self.run_id,
            "issue": self.issue_number,
            "phase": self.phase,
            "status": self.status,
            "pid": os.getpid(),
            "heartbeat": heartbeat,
            "lock": {
                "path": str(self.lock_path),
                "run_id": self.run_id,
            },
            "branch": self.branch,
            "worktree": {
                "path": str(self.worktree) if self.worktree is not None else None,
                "branch": self.branch,
                "base_branch": self.base_branch,
            },
            "plan_reference": str(self.plan_path) if self.plan_path is not None else None,
            "last_known_progress": dict(self.last_known_progress),
            "last_recovery": dict(self.last_recovery)
            if self.last_recovery is not None
            else None,
        }
        tmp_path = self.state_path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(self.state_path)

    def heartbeat(self) -> None:
        self.write()

    def record_event(
        self,
        *,
        event_type: str,
        status: str,
        summary: str,
        attempt: int | None = None,
        duration: float | int | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        metadata = _sanitize_event_metadata(event_type=event_type, metadata=metadata)
        return self._event_stream.append(
            phase=self.phase,
            event_type=event_type,
            status=status,
            summary=summary,
            attempt=attempt,
            duration=duration,
            metadata=metadata,
        )

    def record_recovery(
        self,
        event: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        payload = {
            "timestamp": _isoformat_utc(self._clock()),
            "run_id": self.run_id,
            "issue": self.issue_number,
            "phase": self.phase,
            "event": event,
            **dict(details or {}),
        }
        self.last_recovery = payload
        self.log_dir.mkdir(parents=True, exist_ok=True)
        with (self.log_dir / "recovery.log").open("a", encoding="utf-8") as log:
            log.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        self.record_event(
            event_type="recovery",
            status=_recovery_event_status(event),
            summary=event.replace("_", " "),
            metadata={"event": event, **dict(details or {})},
        )
        self.write(progress=self.last_known_progress)

    def record_browser_observation(
        self,
        *,
        status: str,
        summary: str,
        metadata: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        return self.record_event(
            event_type="browser_observation",
            status=status,
            summary=summary,
            metadata=metadata,
        )


_ACTIVE_RUN_STATE: _RunStateWriter | None = None


class _RunInterruptScope:
    def __init__(self) -> None:
        self._previous_handlers: dict[int, signal.Handlers] = {}

    def __enter__(self) -> _RunInterruptScope:
        for signum in _interrupt_signal_numbers():
            self._previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, _handle_run_interrupt)
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        global _ACTIVE_RUN_STATE
        _ACTIVE_RUN_STATE = None
        for signum, handler in self._previous_handlers.items():
            signal.signal(signum, handler)


def _interrupt_signal_numbers() -> tuple[int, ...]:
    numbers: list[int] = []
    for name in ("SIGTERM", "SIGINT", "SIGHUP"):
        signum = getattr(signal, name, None)
        if signum is not None:
            numbers.append(signum)
    return tuple(numbers)


def _recovery_event_status(event: str) -> str:
    if event.endswith("_blocked"):
        return "block"
    return "success"


def _handle_run_interrupt(signum: int, _frame: object) -> None:
    state = _ACTIVE_RUN_STATE
    if state is not None:
        _record_run_interrupted(state, signum)
    raise _RunInterrupted(f"sympohy interrupted by {_signal_name(signum)}")


def _record_run_interrupted(state: _RunStateWriter, signum: int) -> None:
    signal_name = _signal_name(signum)
    progress = dict(state.last_known_progress)
    progress.update(
        {
            "message": "interrupted by signal",
            "signal": signal_name,
            "resume_action": "resume_interrupted_run",
        }
    )
    state.record_event(
        event_type="command",
        status="interrupted",
        summary="run interrupted by signal",
        metadata={"signal": signal_name},
    )
    state.write(status="interrupted", progress=progress)


def _signal_name(signum: int) -> str:
    try:
        return signal.Signals(signum).name
    except ValueError:
        return str(signum)


def _run_stage_gate(
    stage: str,
    *,
    config: SympohyConfig,
    issue: Issue,
    log_dir: Path,
    context: Mapping[str, object],
    cwd: Path | None = None,
    state: _RunStateWriter | None = None,
) -> Mapping[str, object]:
    if not config.stage_gate_command:
        return {
            "status": "pass",
            "stage": stage,
            "issue": issue.number,
            "reason": "stage gate command is disabled",
        }

    gate_dir = log_dir / "stage-gates"
    gate_dir.mkdir(parents=True, exist_ok=True)
    input_path = gate_dir / f"{stage}-input.json"
    output_path = gate_dir / f"{stage}.json"
    payload = {
        "stage": stage,
        "issue": issue.number,
        "run_dir": str(log_dir),
        "context": _stage_gate_context(context),
    }
    input_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if state is not None:
        state.write(
            progress={
                "message": "running stage gate",
                "stage_gate": stage,
                "stage_gate_input": str(input_path),
                "stage_gate_output": str(output_path),
            }
        )

    command = shlex.split(config.stage_gate_command)
    if command and command[0] == "task":
        command.append("--")
    command += [
        "--stage",
        stage,
        "--issue",
        str(issue.number),
        "--run-dir",
        str(log_dir.resolve()),
        "--input",
        str(input_path.resolve()),
    ]
    started_at = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        result_payload = json.loads(completed.stdout)
        if not isinstance(result_payload, Mapping):
            raise ValueError("stage gate output must be a JSON object")
        result: dict[str, object] = dict(result_payload)
    except (json.JSONDecodeError, ValueError) as exc:
        result = {
            "status": "block",
            "stage": stage,
            "issue": issue.number,
            "reason": f"stage gate command returned invalid JSON: {exc}",
        }
    result["command"] = config.stage_gate_command
    result["returncode"] = completed.returncode
    result["stderr"] = completed.stderr
    if completed.returncode != 0 and result.get("status") == "pass":
        result["status"] = "block"
        result["reason"] = "stage gate command failed after reporting pass"
    if state is not None:
        stage_gate_status = str(result.get("status", "block"))
        reason = str(result.get("reason", "")).strip()
        state.record_event(
            event_type="stage_gate",
            status=stage_gate_status,
            summary=f"{stage} stage gate {stage_gate_status}",
            duration=_elapsed_seconds(started_at),
            metadata={
                "stage": stage,
                "command": config.stage_gate_command,
                "returncode": completed.returncode,
                "failure_summary": reason or _failure_summary(completed.stderr),
            },
        )
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def _stage_gate_context(context: Mapping[str, object]) -> dict[str, object]:
    normalized = dict(context)
    workspace = normalized.get("workspace")
    if isinstance(workspace, str) and workspace.strip():
        workspace_path = Path(workspace)
        if not workspace_path.is_absolute():
            workspace_path = workspace_path.resolve()
        normalized["workspace"] = str(workspace_path)
    return normalized


def _stage_gate_passed(
    stage: str,
    *,
    config: SympohyConfig,
    issue_ref: str,
    issue: Issue,
    log_dir: Path,
    context: Mapping[str, object],
    phase: str,
    cwd: Path | None,
    state: _RunStateWriter,
    current_labels: Sequence[str] | None = None,
) -> bool:
    result = _run_stage_gate(
        stage,
        config=config,
        issue=issue,
        log_dir=log_dir,
        context=context,
        cwd=cwd,
        state=state,
    )
    if result.get("status") == "pass":
        return True
    reason = str(result.get("reason", "stage gate did not pass"))
    _block(
        issue_ref,
        phase=phase,
        failed_command=f"stage gate: {stage}",
        attempts=1,
        cause=f"{result.get('status')}: {reason}",
        run_log_path=log_dir,
        cwd=cwd,
        state=state,
        current_labels=current_labels,
    )
    return False


def _prepare_document_artifacts(
    *,
    config: SympohyConfig,
    issue_ref: str,
    issue: Issue,
    acceptance: AcceptanceSet,
    worktree: Path,
    log_dir: Path,
    state: _RunStateWriter,
) -> bool:
    if not config.stage_gate_command:
        return True

    decisions_path = log_dir / "artifact-decisions.json"
    decisions = _load_artifact_decisions(decisions_path)
    if decisions is None:
        state.write(
            phase="implement",
            worktree=worktree,
            progress={
                "message": "preparing feature documentation artifacts",
                "artifact_decisions_path": str(decisions_path),
            },
        )
        decisions = _request_artifact_decisions(
            config=config,
            issue=issue,
            acceptance=acceptance,
            worktree=worktree,
            log_path=decisions_path,
            heartbeat=state.heartbeat,
            state=state,
        )

    for stage in ("requirements", "design", "wireframes", "adr"):
        for attempt in range(1, DOCUMENT_ARTIFACT_GATE_MAX_ATTEMPTS + 1):
            result = _run_stage_gate(
                stage,
                config=config,
                issue=issue,
                log_dir=log_dir,
                context={
                    "artifact_decisions": decisions,
                    "workspace": str(worktree),
                },
                cwd=worktree,
                state=state,
            )
            if result.get("status") == "pass":
                break
            if result.get("status") == "block":
                _block(
                    issue_ref,
                    phase="implement",
                    failed_command=f"stage gate: {stage}",
                    attempts=attempt,
                    cause=str(result.get("reason", "stage gate blocked")),
                    run_log_path=log_dir,
                    cwd=worktree,
                    state=state,
                    current_labels=("sympohy:running", "sympohy:phase:implement"),
                )
                return False
            if attempt >= DOCUMENT_ARTIFACT_GATE_MAX_ATTEMPTS:
                _block(
                    issue_ref,
                    phase="implement",
                    failed_command=f"stage gate: {stage}",
                    attempts=attempt,
                    cause=(
                        f"{stage} artifact gate did not pass after "
                        f"{DOCUMENT_ARTIFACT_GATE_MAX_ATTEMPTS} attempts: "
                        f"{result.get('reason', 'stage gate retry')}"
                    ),
                    run_log_path=log_dir,
                    cwd=worktree,
                    state=state,
                    current_labels=("sympohy:running", "sympohy:phase:implement"),
                )
                return False
            fix_log_path = log_dir / f"artifact-decisions-{stage}-{attempt + 1}.json"
            state.write(
                phase="implement",
                progress={
                    "message": "repairing feature documentation artifact evidence",
                    "stage_gate": stage,
                    "stage_gate_status": result.get("status"),
                    "stage_gate_reason": result.get("reason"),
                    "artifact_decisions_path": str(fix_log_path),
                    "attempt": attempt + 1,
                    "max_attempts": DOCUMENT_ARTIFACT_GATE_MAX_ATTEMPTS,
                },
            )
            decisions = _request_artifact_decisions(
                config=config,
                issue=issue,
                acceptance=acceptance,
                worktree=worktree,
                log_path=fix_log_path,
                heartbeat=state.heartbeat,
                state=state,
                repair_stage=stage,
                repair_reason=str(result.get("reason", "")),
                previous_decisions=decisions,
            )
            decisions_path.write_text(
                json.dumps(
                    {"artifact_decisions": decisions},
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        else:
            return False
    return True


def _request_artifact_decisions(
    *,
    config: SympohyConfig,
    issue: Issue,
    acceptance: AcceptanceSet,
    worktree: Path,
    log_path: Path,
    heartbeat: Callable[[], None] | None,
    state: _RunStateWriter | None = None,
    repair_stage: str | None = None,
    repair_reason: str | None = None,
    previous_decisions: Mapping[str, object] | None = None,
) -> Mapping[str, object]:
    prompt = [
        "Prepare SIFTQ feature documentation before implementation.",
        "Use .agents/skills/feature-docs-planning/SKILL.md and "
        "docs/contributing/development-flow.md as the rules.",
        "Create or update docs when needed. Then return JSON only.",
        "The JSON object must be: {\"artifact_decisions\": {"
        "\"requirements\": {\"mode\": \"new|existing|not_needed\", "
        "\"path\": \"docs/requirements/...\" or \"reason\": \"...\"}, "
        "\"design\": {\"mode\": \"new|existing|not_needed\", "
        "\"path\": \"docs/design/...\" or \"reason\": \"...\"}, "
        "\"wireframes\": {\"mode\": \"new|existing|not_needed\", "
        "\"path\": \"docs/wireframes/...\" or \"reason\": \"...\"}, "
        "\"adr\": {\"mode\": \"new|existing|not_needed\", "
        "\"path\": \"docs/adr/...\" or \"reason\": \"...\"}}}.",
        "For new or existing modes, the referenced relative path must exist "
        "in the repository when you finish.",
        json.dumps(
            {
                "issue": issue.number,
                "title": issue.title,
                "acceptance_criteria": list(acceptance.acceptance_criteria),
                "definition_of_done": list(acceptance.definition_of_done),
                "repair_stage": repair_stage,
                "repair_reason": repair_reason,
                "previous_decisions": previous_decisions,
            },
            ensure_ascii=False,
        ),
    ]
    payload = _codex_json(
        prompt,
        cwd=worktree,
        log_path=log_path,
        heartbeat=heartbeat,
        config=config,
        role="planning",
        state=state,
    )
    return _artifact_decisions(payload)


def _artifact_decisions(payload: Mapping[str, object]) -> Mapping[str, object]:
    decisions = payload.get("artifact_decisions", payload)
    if not isinstance(decisions, Mapping):
        raise ValueError("artifact decisions JSON must be an object")
    return decisions


def _load_artifact_decisions(path: Path) -> Mapping[str, object] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, Mapping):
        return None
    try:
        return _artifact_decisions(payload)
    except ValueError:
        return None


class _IssueRunLock:
    def __init__(
        self,
        *,
        issue_number: int,
        log_dir: Path,
        run_id: str,
        stale_status_after_minutes: int,
    ) -> None:
        self.issue_number = issue_number
        self.log_dir = log_dir
        self.run_id = run_id
        self.stale_status_after_minutes = stale_status_after_minutes
        self.path = log_dir / "run.lock"
        self.acquired = False

    def __enter__(self) -> _IssueRunLock:
        self.acquire()
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc: object,
        _tb: object,
    ) -> None:
        self.release()

    def acquire(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        payload = _lock_payload(
            run_id=self.run_id,
            issue_number=self.issue_number,
            phase=None,
            heartbeat=_isoformat_utc(datetime.now(timezone.utc)),
        )
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            fd = os.open(self.path, flags, 0o644)
        except FileExistsError as exc:
            if not _lock_takeover_allowed(
                self.path,
                state_path=self.log_dir / "state.json",
                issue_number=self.issue_number,
                stale_status_after_minutes=self.stale_status_after_minutes,
            ):
                raise _RunLockedError(
                    f"issue #{self.issue_number} is already locked by {self.path}"
                ) from exc
            fd = self._take_over_stale_lock(flags)
        with os.fdopen(fd, "w", encoding="utf-8") as lock_file:
            lock_file.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        self.acquired = True

    def _take_over_stale_lock(self, flags: int) -> int:
        guard_path = self.path.with_name(f"{self.path.name}.takeover")
        try:
            guard_fd = os.open(guard_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError as exc:
            raise _RunLockedError(
                f"issue #{self.issue_number} lock takeover is already in progress"
            ) from exc

        try:
            os.close(guard_fd)
            if not _lock_takeover_allowed(
                self.path,
                state_path=self.log_dir / "state.json",
                issue_number=self.issue_number,
                stale_status_after_minutes=self.stale_status_after_minutes,
            ):
                raise _RunLockedError(
                    f"issue #{self.issue_number} is already locked by {self.path}"
                )
            self.path.unlink(missing_ok=True)
            try:
                return os.open(self.path, flags, 0o644)
            except FileExistsError as retry_exc:
                raise _RunLockedError(
                    f"issue #{self.issue_number} is already locked by {self.path}"
                ) from retry_exc
        finally:
            guard_path.unlink(missing_ok=True)

    def release(self) -> None:
        if not self.acquired:
            return
        payload = read_run_state(self.path)
        if payload is not None and payload.get("run_id") == self.run_id:
            self.path.unlink(missing_ok=True)
        self.acquired = False


def ensure_worktree(issue: Issue, config: SympohyConfig, *, recover: bool = False) -> Path:
    worktree = config.worktree_root / f"issue-{issue.number}"
    branch = f"issue-{issue.number}-sympohy"
    if worktree.exists():
        if not recover:
            raise _ExistingRunError(
                f"worktree already exists for issue #{issue.number}: {worktree}; use resume"
            )
        try:
            current_branch = _current_branch(worktree)
        except subprocess.CalledProcessError as exc:
            raise _UnsafeRecoveryError(
                f"cannot recover issue #{issue.number}: could not inspect current branch "
                f"for worktree {worktree}"
            ) from exc
        if current_branch != branch:
            raise _UnsafeRecoveryError(
                f"cannot recover issue #{issue.number}: worktree {worktree} is on "
                f"branch {current_branch}, expected {branch}"
            )
        return worktree

    worktree.parent.mkdir(parents=True, exist_ok=True)
    if _branch_exists(branch):
        if not recover:
            raise _ExistingRunError(
                f"existing branch found for issue #{issue.number}: {branch}; use resume"
            )
        existing_worktree = _worktree_for_branch(branch)
        if existing_worktree is not None:
            return existing_worktree
        subprocess.check_call(["git", "worktree", "add", str(worktree), branch])
    elif recover and _remote_branch_exists(branch):
        subprocess.check_call(
            [
                "git",
                "worktree",
                "add",
                "-b",
                branch,
                str(worktree),
                f"origin/{branch}",
            ]
        )
    elif recover:
        raise _UnsafeRecoveryError(
            f"cannot recover issue #{issue.number}: neither worktree {worktree} "
            f"nor existing branch {branch} was found"
        )
    else:
        subprocess.check_call(
            ["git", "worktree", "add", "-b", branch, str(worktree), config.base_branch]
        )
    return worktree


def watch(config: SympohyConfig) -> int:
    return watch_forever(
        config,
        poll_interval_seconds=config.watch_poll_interval_seconds,
    )


def watch_forever(
    config: SympohyConfig,
    *,
    poll_interval_seconds: int,
    stop_after_polls: int | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    active: dict[int, subprocess.Popen[bytes]] = {}
    failed = False
    polls = 0

    while stop_after_polls is None or polls < stop_after_polls:
        failed = _reap_watch_workers(active) or failed
        _start_watch_workers(config, active)
        polls += 1

        if stop_after_polls is not None and polls >= stop_after_polls:
            break
        sleep(poll_interval_seconds)

    returncodes = [process.wait() for process in active.values()]
    active.clear()
    return 0 if not failed and all(code == 0 for code in returncodes) else 1


def _reap_watch_workers(
    active: dict[int, subprocess.Popen[bytes]],
) -> bool:
    failed = False
    for number, process in list(active.items()):
        returncode = process.poll()
        if returncode is None:
            continue
        if returncode != 0:
            failed = True
        del active[number]
    return failed


def _start_watch_workers(
    config: SympohyConfig,
    active: dict[int, subprocess.Popen[bytes]],
) -> None:
    available_slots = config.max_workers - len(active)
    if available_slots <= 0:
        return

    candidates = list_candidate_issues(
        limit=100,
        run_log_root=config.run_log_root,
        stale_status_after_minutes=config.stale_status_after_minutes,
    )
    selected = sorted(candidates, key=_watch_candidate_priority)

    for issue in selected:
        if len(active) >= config.max_workers:
            return
        number = int(issue["number"])
        if number in active:
            continue
        command = _watch_worker_command(issue, config)
        if command is None:
            continue
        active[number] = subprocess.Popen(command)


def _watch_worker_command(
    issue: Mapping[str, object],
    config: SympohyConfig,
) -> list[str] | None:
    number = int(issue["number"])
    labels = _label_names(issue.get("labels", []))
    if "sympohy:pending" in labels or "sympohy:running" in labels:
        inspection = inspect_running_issue(
            issue,
            run_log_root=config.run_log_root,
            stale_status_after_minutes=config.stale_status_after_minutes,
        )
        if not inspection.stale:
            return None
        return [
            sys.executable,
            "-m",
            "scripts.sympohy",
            "resume",
            f"#{number}",
        ]

    return [
        sys.executable,
        "-m",
        "scripts.sympohy",
        "run",
        f"#{number}",
    ]


def _watch_candidate_priority(issue: Mapping[str, object]) -> int:
    labels = set(_label_names(issue.get("labels", [])))
    if "sympohy:running" in labels:
        return 0
    if "sympohy:pending" in labels:
        return 1
    return 2


def resume_issue(issue_ref: str, config: SympohyConfig) -> int:
    issue = fetch_issue(issue_ref)
    labels = [{"name": label} for label in issue.labels]
    log_dir = config.run_log_root / f"issue-{issue.number}"
    state_path = log_dir / "state.json"
    state_payload = read_run_state(state_path)
    resume_point = _resolve_resume_point_for_issue(
        labels,
        state_payload,
        issue_state=issue.state,
        issue_state_reason=issue.state_reason,
    )

    if resume_point.terminal:
        terminal_phase = resume_point.phase or (
            "finalize" if resume_point.name == "completed" else "triage"
        )
        run_id = _new_run_id()
        lock = _IssueRunLock(
            issue_number=issue.number,
            log_dir=log_dir,
            run_id=run_id,
            stale_status_after_minutes=config.stale_status_after_minutes,
        )
        try:
            lock.acquire()
        except _RunLockedError:
            return 0
        try:
            state = _RunStateWriter(
                issue_number=issue.number,
                log_dir=log_dir,
                base_branch=config.base_branch,
                run_id=run_id,
                lock_path=lock.path,
                refresh_lock=True,
            )
            state.write(
                phase=terminal_phase,
                status="done" if resume_point.name == "completed" else resume_point.name,
                progress={
                    "message": "reconciling terminal issue state",
                    "resume_point": resume_point.name,
                },
            )
            state.record_recovery(
                "terminal_state_reconciled",
                {
                    "resume_point": resume_point.name,
                    "phase": terminal_phase,
                },
            )
            _reconcile_terminal_issue_state(
                issue_ref,
                issue,
                terminal_name=resume_point.name,
                phase=terminal_phase,
            )
        finally:
            lock.release()
        return 0

    payload = {
        "number": issue.number,
        "state": issue.state,
        "labels": labels,
    }
    inspection = inspect_running_issue(
        payload,
        run_log_root=config.run_log_root,
        stale_status_after_minutes=config.stale_status_after_minutes,
    )
    if not inspection.stale:
        return 0

    if (
        "sympohy:pending" in issue.labels
        and "sympohy:running" not in issue.labels
        and resume_point.name == "planning"
        and inspection.state is None
    ):
        return run_issue(
            issue_ref,
            config,
            recover=False,
            from_resume=_issue_branch_exists(issue),
            resume_point=resume_point.name,
        )

    run_id = _new_run_id()
    lock = _IssueRunLock(
        issue_number=issue.number,
        log_dir=log_dir,
        run_id=run_id,
        stale_status_after_minutes=config.stale_status_after_minutes,
    )
    try:
        lock.acquire()
    except _RunLockedError:
        return 0
    try:
        state_payload = read_run_state(state_path)
        resume_point = _resolve_resume_point_for_issue(
            labels,
            state_payload,
            issue_state=issue.state,
            issue_state_reason=issue.state_reason,
        )
        if resume_point.terminal:
            return 0

        inspection = inspect_running_issue(
            payload,
            run_log_root=config.run_log_root,
            stale_status_after_minutes=config.stale_status_after_minutes,
        )
        if not inspection.stale:
            return 0

        if inspection.state is None or inspection.reason in {"missing phase", "corrupt state"}:
            bootstrap_phase = inspection.phase or _phase_from_labels(issue.labels) or "triage"
            state_payload = _bootstrap_run_state(
                issue,
                config,
                log_dir,
                phase=bootstrap_phase,
                reason=inspection.reason,
                run_id=run_id,
                lock_path=lock.path,
            )
            resume_point = _resolve_resume_point_for_issue(
                labels,
                state_payload,
                issue_state=issue.state,
                issue_state_reason=issue.state_reason,
            )
        elif inspection.reason == "invalid state":
            phase = inspection.phase or _phase_from_labels(issue.labels) or "triage"
            state = _RunStateWriter(
                issue_number=issue.number,
                log_dir=log_dir,
                base_branch=config.base_branch,
                run_id=run_id,
                lock_path=lock.path,
                refresh_lock=True,
            )
            cause = (
                f"invalid run state for issue #{issue.number}; refusing automatic resume"
            )
            if inspection.state_path is not None:
                cause = f"{cause}: {inspection.state_path}"
            state.record_recovery(
                "unsafe_recovery_blocked",
                {
                    "cause": cause,
                    "resume_point": resume_point.name,
                    "stale_reason": inspection.reason,
                },
            )
            _block(
                issue_ref,
                phase=phase,
                failed_command="resume safety check",
                attempts=1,
                cause=cause,
                run_log_path=log_dir,
                cwd=None,
                state=state,
                current_labels=issue.labels,
            )
            return 2

        phase = inspection.phase or resume_point.phase or "triage"
        if phase != _phase_from_labels(issue.labels):
            set_issue_state(
                issue_ref,
                current_labels=issue.labels,
                status="sympohy:running",
                phase=phase,
            )
    finally:
        lock.release()

    recover = resume_point.name != "planning"
    resume_from = resume_point.name
    if _should_resume_missing_plan_as_planning(
        resume_point=resume_point.name,
        state=state_payload,
        plan_path=log_dir / "plan.json",
    ):
        recover = False
        resume_from = "planning"

    return run_issue(
        issue_ref,
        config,
        recover=recover,
        from_resume=True,
        resume_point=resume_from,
    )


def _reconcile_terminal_issue_state(
    issue_ref: str,
    issue: Issue,
    *,
    terminal_name: str,
    phase: str,
) -> None:
    if terminal_name == "completed":
        if (
            "sympohy:done" not in issue.labels
            or _phase_from_labels(issue.labels) != phase
        ):
            set_issue_state(
                issue_ref,
                current_labels=issue.labels,
                status="sympohy:done",
                phase=phase,
            )
        if issue.state in {"OPEN", "open"}:
            subprocess.check_call(["gh", "issue", "close", issue_ref])
        return

    if terminal_name == "blocked" and (
        "sympohy:blocked" not in issue.labels
        or _phase_from_labels(issue.labels) != phase
    ):
        set_issue_state(
            issue_ref,
            current_labels=issue.labels,
            status="sympohy:blocked",
            phase=phase,
        )


def refine_issue(issue_ref: str) -> tuple[int, str]:
    issue = fetch_issue(issue_ref)
    acceptance = extract_acceptance_set(issue.body, issue.comments)
    if acceptance is None:
        body = (
            "sympohy blocked this issue during triage.\n\n"
            "- phase: triage\n"
            "- reason: AC/DoD の完全なセットを issue body/comments から確認できませんでした\n"
        )
        set_issue_state(
            issue_ref,
            current_labels=issue.labels,
            status="sympohy:blocked",
            phase="triage",
        )
        comment(issue_ref, body)
        return 2, body

    payload = {
        "issue": issue.number,
        "source": acceptance.source,
        "acceptance_criteria": list(acceptance.acceptance_criteria),
        "definition_of_done": list(acceptance.definition_of_done),
    }
    return 0, json.dumps(payload, ensure_ascii=False, indent=2)


def run_issue(
    issue_ref: str,
    config: SympohyConfig,
    *,
    recover: bool = False,
    from_resume: bool = False,
    resume_point: str | None = None,
) -> int:
    issue = fetch_issue(issue_ref)
    log_dir = config.run_log_root / f"issue-{issue.number}"
    run_id = _new_run_id()
    lock = _IssueRunLock(
        issue_number=issue.number,
        log_dir=log_dir,
        run_id=run_id,
        stale_status_after_minutes=config.stale_status_after_minutes,
    )
    try:
        lock.acquire()
    except _RunLockedError:
        return 0
    try:
        with _RunInterruptScope():
            try:
                return _run_issue_locked(
                    issue_ref,
                    config,
                    issue=issue,
                    recover=recover,
                    from_resume=from_resume,
                    resume_point=resume_point,
                    run_id=run_id,
                    lock_path=lock.path,
                )
            except _RunInterrupted:
                return 130
    finally:
        lock.release()


def _run_issue_locked(
    issue_ref: str,
    config: SympohyConfig,
    *,
    issue: Issue,
    recover: bool,
    from_resume: bool,
    resume_point: str | None,
    run_id: str,
    lock_path: Path,
) -> int:
    log_dir = config.run_log_root / f"issue-{issue.number}"
    previous_state = read_run_state(log_dir / "state.json")
    resume_from = resume_point or ("implement" if recover else "planning")
    resume_from = PHASE_ALIASES.get(resume_from, resume_from)
    if resume_from not in {"planning", "implement", "hooks", "review", "fix", "finalize"}:
        raise ValueError(f"unknown resume point: {resume_from}")
    state = _RunStateWriter(
        issue_number=issue.number,
        log_dir=log_dir,
        base_branch=config.base_branch,
        run_id=run_id,
        lock_path=lock_path,
        refresh_lock=True,
    )
    global _ACTIVE_RUN_STATE
    _ACTIVE_RUN_STATE = state
    if not recover and not from_resume:
        existing_run_reason = _existing_run_refusal_reason(issue, config, log_dir)
        if existing_run_reason is not None:
            phase = (
                phase_from_state(read_run_state(log_dir / "state.json"))
                or _phase_from_labels(issue.labels)
                or "triage"
            )
            state.write(
                phase=phase,
                status="blocked",
                progress={
                    "message": "fresh run refused; use resume",
                    "cause": existing_run_reason,
                },
            )
            _block(
                issue_ref,
                phase=phase,
                failed_command="run safety check",
                attempts=1,
                cause=existing_run_reason,
                run_log_path=log_dir,
                cwd=None,
                state=state,
                current_labels=issue.labels,
            )
            return 2
        set_issue_state(
            issue_ref,
            current_labels=issue.labels,
            status="sympohy:pending",
            phase="triage",
        )

    if from_resume and resume_from in {"review", "fix", "finalize"}:
        return _resume_late_phase(
            issue_ref,
            issue,
            config,
            log_dir,
            state,
            previous_state=previous_state,
            resume_from=resume_from,
        )

    state.write(
        phase="triage",
        progress={"message": "checking acceptance criteria and definition of done"},
    )
    acceptance = extract_acceptance_set(issue.body, issue.comments)
    if acceptance is None:
        state.write(
            phase="triage",
            status="blocked",
            progress={"message": "missing complete acceptance criteria or definition of done"},
        )
        message = (
            "sympohy blocked this issue during triage.\n\n"
            "- phase: triage\n"
            "- reason: AC/DoD の完全なセットを issue body/comments から確認できませんでした\n"
        )
        set_issue_state(
            issue_ref,
            current_labels=issue.labels,
            status="sympohy:blocked",
            phase="triage",
        )
        comment(issue_ref, message)
        return 2

    if not _stage_gate_passed(
        "request-elaboration",
        config=config,
        issue_ref=issue_ref,
        issue=issue,
        log_dir=log_dir,
        context={
            "acceptance_criteria": list(acceptance.acceptance_criteria),
            "definition_of_done": list(acceptance.definition_of_done),
        },
        phase="triage",
        cwd=None,
        state=state,
        current_labels=issue.labels,
    ):
        return 2

    try:
        worktree = ensure_worktree(
            issue,
            config,
            recover=recover or (from_resume and _issue_branch_exists(issue)),
        )
    except (_ExistingRunError, _UnsafeRecoveryError) as exc:
        phase = resume_from if resume_from != "planning" else "implement"
        state.write(
            phase=phase,
            status="blocked",
            progress={
                "message": "unsafe resume blocked",
                "cause": str(exc),
            },
        )
        state.record_recovery(
            "unsafe_recovery_blocked",
            {
                "cause": str(exc),
                "resume_point": resume_from,
            },
        )
        _block(
            issue_ref,
            phase=phase,
            failed_command="resume safety check",
            attempts=1,
            cause=str(exc),
            run_log_path=log_dir,
            cwd=None,
            state=state,
            current_labels=issue.labels,
        )
        return 2
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        branch = _current_branch(worktree)
    except subprocess.CalledProcessError:
        if not recover:
            raise
        state.write(
            phase="implement",
            worktree=worktree,
            progress={"message": "unsafe resume blocked"},
        )
        _block(
            issue_ref,
            phase="implement",
            failed_command="resume safety check",
            attempts=1,
            cause=f"could not inspect current branch for worktree {worktree}",
            run_log_path=log_dir,
            cwd=None,
            state=state,
            current_labels=issue.labels,
        )
        return 2
    plan_path = log_dir / "plan.json"
    state.write(
        phase="implement",
        worktree=worktree,
        branch=branch,
        plan_path=plan_path,
        progress={"message": "starting implementation planning"},
    )

    set_issue_state(
        issue_ref,
        current_labels=issue.labels,
        status="sympohy:running",
        phase="implement",
    )
    initial_pull_request_ensured = False
    if not recover:
        state.write(
            phase="implement",
            branch=branch,
            progress={
                "message": "pushing initial issue branch and opening draft pull request",
                "pull_request_timing": "after_branch_creation",
            },
        )
        try:
            _push_branch_and_ensure_draft_pull_request(
                cwd=worktree,
                branch=branch,
                heartbeat=state.heartbeat,
                issue_number=issue.number,
                base_branch=config.base_branch,
                state=state,
            )
        except (_AmbiguousPullRequestError, _PullRequestMetadataError) as exc:
            _block(
                issue_ref,
                phase="review",
                failed_command="pull request safety check",
                attempts=1,
                cause=str(exc),
                run_log_path=log_dir,
                cwd=worktree,
                state=state,
                current_labels=("sympohy:running", "sympohy:phase:implement"),
            )
            return 2
        initial_pull_request_ensured = True

    if not _prepare_document_artifacts(
        config=config,
        issue_ref=issue_ref,
        issue=issue,
        acceptance=acceptance,
        worktree=worktree,
        log_dir=log_dir,
        state=state,
    ):
        return 2

    plan = _load_existing_plan(plan_path) if recover else None
    loaded_existing_plan = plan is not None
    if recover and plan is None:
        _block(
            issue_ref,
            phase="implement",
            failed_command="resume safety check",
            attempts=1,
            cause=f"missing or invalid saved implementation plan at {plan_path}",
            run_log_path=log_dir,
            cwd=worktree,
            state=state,
            current_labels=("sympohy:running", "sympohy:phase:implement"),
        )
        return 2
    if plan is None:
        plan = _codex_json(
            [
                "You are implementing SIFTQ GitHub Issue "
                f"#{issue.number}. Produce JSON with key logical_steps, an array "
                "of implementation steps. Use the issue AC/DoD as source of truth.",
                json.dumps(
                    {
                        "title": issue.title,
                        "acceptance_criteria": list(acceptance.acceptance_criteria),
                        "definition_of_done": list(acceptance.definition_of_done),
                    },
                    ensure_ascii=False,
                ),
            ],
            cwd=worktree,
            log_path=plan_path,
            heartbeat=state.heartbeat,
            config=config,
            role="planning",
            state=state,
        )
    logical_steps = _logical_steps(plan)
    total_steps = len(logical_steps)
    if from_resume and resume_from == "hooks":
        hook_step = _progress_int(previous_state, "current_logical_step")
        if hook_step is None or hook_step < 1 or hook_step > total_steps:
            _block(
                issue_ref,
                phase="hooks",
                failed_command="resume safety check",
                attempts=1,
                cause="saved hooks phase is missing a valid current_logical_step",
                run_log_path=log_dir,
                cwd=worktree,
                state=state,
                current_labels=("sympohy:running", "sympohy:phase:hooks"),
            )
            return 2
        recovery = _ImplementationRecovery(
            committed_logical_steps=hook_step - 1,
            worktree_logical_step=hook_step,
            worktree_clean=False,
        )
    elif recover:
        recovery = _infer_implementation_recovery(
            issue.number,
            cwd=worktree,
            base_branch=config.base_branch,
            total_steps=total_steps,
        )
    else:
        recovery = _ImplementationRecovery(committed_logical_steps=0)
    if recovery.unsafe_reason is not None:
        state.write(
            phase="implement",
            status="blocked",
            progress={
                "message": "unsafe resume blocked",
                "cause": recovery.unsafe_reason,
                "plan_log_path": str(plan_path),
                "recovered_existing_plan": loaded_existing_plan,
                "worktree_clean": recovery.worktree_clean,
            },
        )
        state.record_recovery(
            "unsafe_recovery_blocked",
            {
                "cause": recovery.unsafe_reason,
                "resume_point": resume_from,
                "completed_logical_steps": recovery.committed_logical_steps,
                "total_logical_steps": total_steps,
                "worktree_clean": recovery.worktree_clean,
            },
        )
        _block(
            issue_ref,
            phase="implement",
            failed_command="resume safety check",
            attempts=1,
            cause=recovery.unsafe_reason,
            run_log_path=log_dir,
            cwd=worktree,
            state=state,
            current_labels=("sympohy:running", "sympohy:phase:implement"),
        )
        return 2
    next_logical_step = recovery.next_logical_step(total_steps)
    if recover or from_resume:
        state.record_recovery(
            "implementation_recovery_inspected",
            {
                "resume_point": resume_from,
                "completed_logical_steps": recovery.committed_logical_steps,
                "total_logical_steps": total_steps,
                "worktree_clean": recovery.worktree_clean,
                "worktree_logical_step": recovery.worktree_logical_step,
                "next_logical_step": next_logical_step,
                "resume_action": recovery.resume_action(total_steps),
                "recovered_existing_plan": loaded_existing_plan,
            },
        )
    state.write(
        phase="implement",
        progress={
            "message": "implementation plan loaded"
            if loaded_existing_plan
            else "implementation plan generated",
            "completed_logical_steps": recovery.committed_logical_steps,
            "total_logical_steps": total_steps,
            "plan_log_path": str(plan_path),
            "recovered_existing_plan": loaded_existing_plan,
            "worktree_logical_step": recovery.worktree_logical_step,
            "next_logical_step": next_logical_step,
            "resume_action": recovery.resume_action(total_steps),
            "worktree_clean": recovery.worktree_clean,
            "implementation_complete": recovery.implementation_complete(total_steps),
        },
    )

    if not _stage_gate_passed(
        "implementation",
        config=config,
        issue_ref=issue_ref,
        issue=issue,
        log_dir=log_dir,
        context={
            "branch": branch,
            "plan_path": str(plan_path),
            "total_steps": total_steps,
        },
        phase="implement",
        cwd=worktree,
        state=state,
        current_labels=("sympohy:running", "sympohy:phase:implement"),
    ):
        return 2

    if not initial_pull_request_ensured:
        state.write(
            phase="implement",
            branch=branch,
            progress={
                "message": "pushing initial issue branch and opening draft pull request",
                "pull_request_timing": "after_branch_creation",
            },
        )
        try:
            _push_branch_and_ensure_draft_pull_request(
                cwd=worktree,
                branch=branch,
                heartbeat=state.heartbeat,
                issue_number=issue.number,
                base_branch=config.base_branch,
                state=state,
            )
        except (_AmbiguousPullRequestError, _PullRequestMetadataError) as exc:
            _block(
                issue_ref,
                phase="review",
                failed_command="pull request safety check",
                attempts=1,
                cause=str(exc),
                run_log_path=log_dir,
                cwd=worktree,
                state=state,
                current_labels=("sympohy:running", "sympohy:phase:implement"),
            )
            return 2

    if next_logical_step is None:
        state.write(
            phase="implement",
            progress={
                "message": "implementation already complete; proceeding to push and pull request",
                "completed_logical_steps": total_steps,
                "total_logical_steps": total_steps,
                "resume_action": "push_pr",
                "worktree_clean": recovery.worktree_clean,
            },
        )
    else:
        existing_commit_subjects = set(
            _commit_subjects(
                cwd=worktree,
                base_branch=config.base_branch,
            )
        )
        for index, step in enumerate(logical_steps, start=1):
            if index < next_logical_step:
                continue
            subject = f"#{issue.number} feat(sympohy): implement logical step {index}"
            if not validate_commit_subject(subject):
                raise ValueError(f"invalid generated commit subject: {subject}")
            if _commit_subject_exists(
                subject,
                cwd=worktree,
                base_branch=config.base_branch,
                existing_subjects=existing_commit_subjects,
            ):
                state.write(
                    phase="implement",
                    progress={
                        "message": "logical step commit already exists",
                        "completed_logical_steps": index,
                        "total_logical_steps": total_steps,
                        "commit_subject": subject,
                    },
                )
                continue
            set_issue_state(
                issue_ref,
                current_labels=("sympohy:running", "sympohy:phase:implement"),
                status="sympohy:running",
                phase="implement",
                cwd=worktree,
            )
            implement_log_path = log_dir / f"implement-{index}.log"
            reuse_worktree = recovery.should_reuse_worktree(index)
            state.write(
                phase="implement",
                progress={
                    "message": "resuming logical step from existing worktree changes"
                    if reuse_worktree
                    else "implementing logical step",
                    "current_logical_step": index,
                    "completed_logical_steps": index - 1,
                    "total_logical_steps": total_steps,
                    "log_path": str(implement_log_path),
                    "reused_worktree_changes": reuse_worktree,
                    "resume_action": recovery.resume_action(total_steps),
                    "worktree_clean": recovery.worktree_clean,
                },
            )
            if not reuse_worktree:
                _codex_text(
                    [
                        f"Implement logical step {index} for SIFTQ issue #{issue.number}.",
                        "Before editing or committing, read the relevant "
                        "docs/contributing documents, including "
                        "docs/contributing/branch-strategy.md and "
                        "docs/contributing/commit-message-format.md.",
                        json.dumps(step, ensure_ascii=False),
                        "Use normal Codex user config and repository rules.",
                    ],
                    cwd=worktree,
                    log_path=implement_log_path,
                    heartbeat=state.heartbeat,
                    config=config,
                    role="implementation",
                    state=state,
                )
            state.write(
                phase="hooks",
                progress={
                    "message": "running scoped validation and repository gate",
                    "current_logical_step": index,
                    "completed_logical_steps": index,
                    "total_logical_steps": total_steps,
                },
            )
            if _run_preflight_validations(
                config.ci_retry_max_attempts,
                worktree,
                log_dir,
                config=config,
                state=state,
                logical_step=index,
                total_logical_steps=total_steps,
            ) != 0:
                _block(
                    issue_ref,
                    phase="hooks",
                    failed_command="scoped validation",
                    attempts=config.ci_retry_max_attempts,
                    cause="scoped validation still failed after retries",
                    run_log_path=log_dir,
                    cwd=worktree,
                    state=state,
                )
                return 2
            if _run_hooks(
                config.hooks,
                config.ci_retry_max_attempts,
                worktree,
                log_dir,
                config=config,
                state=state,
                logical_step=index,
                total_logical_steps=total_steps,
            ) != 0:
                _block(
                    issue_ref,
                    phase="hooks",
                    failed_command="; ".join(config.hooks),
                    attempts=config.ci_retry_max_attempts,
                    cause="verification hooks still failed after retries",
                    run_log_path=log_dir,
                    cwd=worktree,
                    state=state,
                )
                return 2
            if not _stage_gate_passed(
                "ci",
                config=config,
                issue_ref=issue_ref,
                issue=issue,
                log_dir=log_dir,
                context={
                    "ci_passed": True,
                    "current_logical_step": index,
                    "total_logical_steps": total_steps,
                },
                phase="hooks",
                cwd=worktree,
                state=state,
                current_labels=("sympohy:running", "sympohy:phase:hooks"),
            ):
                return 2
            committed = _commit_all_if_new(
                subject,
                cwd=worktree,
                base_branch=config.base_branch,
                allow_empty=True,
                existing_subjects=existing_commit_subjects,
            )
            state.write(
                phase="implement",
                progress={
                    "message": "committed logical step"
                    if committed
                    else "logical step commit already exists",
                    "completed_logical_steps": index,
                    "total_logical_steps": total_steps,
                    "commit_subject": subject,
                },
            )

    branch = subprocess.check_output(
        ["git", "branch", "--show-current"],
        cwd=worktree,
        text=True,
    ).strip()
    state.write(
        phase="implement",
        branch=branch,
        progress={
            "message": "pushing branch updates and ensuring draft pull request exists",
            "completed_logical_steps": total_steps,
            "total_logical_steps": total_steps,
        },
    )
    try:
        _push_branch_and_ensure_draft_pull_request(
            cwd=worktree,
            branch=branch,
            issue_number=issue.number,
            heartbeat=state.heartbeat,
            base_branch=config.base_branch,
            state=state,
        )
    except (_AmbiguousPullRequestError, _PullRequestMetadataError) as exc:
        _block(
            issue_ref,
            phase="review",
            failed_command="pull request safety check",
            attempts=1,
            cause=str(exc),
            run_log_path=log_dir,
            cwd=worktree,
            state=state,
            current_labels=("sympohy:running", "sympohy:phase:implement"),
        )
        return 2
    state.write(
        phase="review",
        branch=branch,
        progress={
            "message": "draft pull request ready for review",
            "completed_logical_steps": total_steps,
            "total_logical_steps": total_steps,
        },
    )
    review_result = _review_fix_loop(issue_ref, issue, config, worktree, log_dir, state)
    if review_result != 0:
        return review_result
    if not _stage_gate_passed(
        "review",
        config=config,
        issue_ref=issue_ref,
        issue=issue,
        log_dir=log_dir,
        context={"review_approved": True},
        phase="review",
        cwd=worktree,
        state=state,
        current_labels=("sympohy:running", "sympohy:phase:review"),
    ):
        return 2

    return _run_final_verifier_and_merge(
        issue_ref,
        issue,
        config,
        worktree,
        log_dir,
        state,
        total_steps=total_steps,
    )


def _resume_late_phase(
    issue_ref: str,
    issue: Issue,
    config: SympohyConfig,
    log_dir: Path,
    state: _RunStateWriter,
    *,
    previous_state: Mapping[str, object] | None,
    resume_from: str,
) -> int:
    try:
        worktree = ensure_worktree(issue, config, recover=True)
    except _UnsafeRecoveryError as exc:
        state.write(
            phase=resume_from,
            status="blocked",
            progress={"message": "unsafe resume blocked", "cause": str(exc)},
        )
        state.record_recovery(
            "unsafe_recovery_blocked",
            {
                "cause": str(exc),
                "resume_point": resume_from,
            },
        )
        _block(
            issue_ref,
            phase=resume_from,
            failed_command="resume safety check",
            attempts=1,
            cause=str(exc),
            run_log_path=log_dir,
            cwd=None,
            state=state,
            current_labels=("sympohy:running", f"sympohy:phase:{resume_from}"),
        )
        return 2
    try:
        branch = _current_branch(worktree)
    except subprocess.CalledProcessError:
        state.write(
            phase=resume_from,
            worktree=worktree,
            status="blocked",
            progress={"message": "unsafe resume blocked"},
        )
        _block(
            issue_ref,
            phase=resume_from,
            failed_command="resume safety check",
            attempts=1,
            cause=f"could not inspect current branch for worktree {worktree}",
            run_log_path=log_dir,
            cwd=None,
            state=state,
            current_labels=("sympohy:running", f"sympohy:phase:{resume_from}"),
        )
        return 2

    plan_path = log_dir / "plan.json"
    state.write(
        phase=resume_from,
        worktree=worktree,
        branch=branch,
        plan_path=plan_path if plan_path.exists() else None,
        progress={
            "message": f"resuming {resume_from} phase",
            "resume_point": resume_from,
        },
    )
    state.record_recovery(
        "late_phase_recovery_resumed",
        {
            "resume_point": resume_from,
            "branch": branch,
            "worktree": str(worktree),
        },
    )
    if resume_from in {"review", "finalize"}:
        dirty_result = _block_dirty_late_phase_resume(
            issue_ref,
            resume_from=resume_from,
            worktree=worktree,
            log_dir=log_dir,
            state=state,
        )
        if dirty_result is not None:
            return dirty_result
    if _pull_request_merged(cwd=worktree):
        return _finish_merged_issue(
            issue_ref,
            worktree,
            state,
            total_steps=_progress_int(previous_state, "total_logical_steps"),
            message="reconciled already-merged pull request",
        )
    set_issue_state(
        issue_ref,
        current_labels=issue.labels,
        status="sympohy:running",
        phase=resume_from,
        cwd=worktree,
    )

    if resume_from == "finalize":
        return _run_final_verifier_and_merge(
            issue_ref,
            issue,
            config,
            worktree,
            log_dir,
            state,
            total_steps=_progress_int(previous_state, "total_logical_steps"),
        )
    if resume_from == "fix":
        fix_result = _resume_fix_phase(
            issue_ref,
            issue,
            config,
            worktree,
            log_dir,
            state,
            previous_state=previous_state,
        )
        if fix_result != 0:
            return fix_result
    else:
        state.write(
            phase="review",
            worktree=worktree,
            branch=branch,
            plan_path=plan_path if plan_path.exists() else None,
            progress={
                "message": "ensuring draft pull request exists before review",
                "resume_point": resume_from,
            },
        )
        try:
            _push_branch_and_ensure_draft_pull_request(
                cwd=worktree,
                branch=branch,
                issue_number=issue.number,
                heartbeat=state.heartbeat,
                base_branch=config.base_branch,
                state=state,
            )
        except (_AmbiguousPullRequestError, _PullRequestMetadataError) as exc:
            _block(
                issue_ref,
                phase="review",
                failed_command="pull request safety check",
                attempts=1,
                cause=str(exc),
                run_log_path=log_dir,
                cwd=worktree,
                state=state,
                current_labels=("sympohy:running", f"sympohy:phase:{resume_from}"),
            )
            return 2
        start_round = _review_start_round(previous_state)
        review_result = _review_fix_loop(
            issue_ref,
            issue,
            config,
            worktree,
            log_dir,
            state,
            start_round=start_round,
        )
        if review_result != 0:
            return review_result

    return _run_final_verifier_and_merge(
        issue_ref,
        issue,
        config,
        worktree,
        log_dir,
        state,
        total_steps=_progress_int(previous_state, "total_logical_steps"),
    )


def _resolve_pull_request_number(cwd: Path) -> str:
    return subprocess.check_output(
        ["gh", "pr", "view", "--json", "number", "--jq", ".number"],
        cwd=cwd,
        text=True,
    ).strip()


def _run_review_fix_round(
    issue_ref: str,
    issue: Issue,
    config: SympohyConfig,
    cwd: Path,
    log_dir: Path,
    state: _RunStateWriter,
    *,
    round_index: int,
    review: ReviewResult,
    review_json: str,
    review_pull_request: str,
    comment_review: bool,
    existing_fix_subjects: set[str] | None = None,
) -> int:
    if review.approved:
        if comment_review:
            comment(review_pull_request, review_json, cwd=cwd)
        return 0
    if comment_review:
        comment(review_pull_request, review_json, cwd=cwd)
    if review.stage_gate_status == "block":
        _block(
            issue_ref,
            phase="review",
            failed_command="adversarial review",
            attempts=round_index,
            cause="adversarial review requested manual block",
            run_log_path=log_dir,
            cwd=cwd,
            state=state,
        )
        return 2
    if not review.blocking_findings:
        _block(
            issue_ref,
            phase="review",
            failed_command="adversarial review",
            attempts=round_index,
            cause="review status did not pass but no blocking findings were provided",
            run_log_path=log_dir,
            cwd=cwd,
            state=state,
        )
        return 2
    if round_index > config.review_max_rounds:
        _block(
            issue_ref,
            phase="review",
            failed_command="adversarial review",
            attempts=round_index,
            cause="blocking findings remained after review/fix loop",
            run_log_path=log_dir,
            cwd=cwd,
            state=state,
            details={
                "remaining blocking findings": _summarize_review_findings(
                    review.blocking_findings
                )
            },
        )
        return 2

    subject = f"#{issue.number} fix(sympohy): resolve review finding {round_index}"
    if _worktree_has_changes(cwd):
        cause = (
            "fix phase worktree has uncommitted changes during resume: "
            f"{_summarize_status(_worktree_status(cwd))}"
        )
        state.record_recovery(
            "unsafe_recovery_blocked",
            {
                "cause": cause,
                "resume_point": "fix",
                "review_round": round_index,
            },
        )
        _block(
            issue_ref,
            phase="fix",
            failed_command="resume safety check",
            attempts=1,
            cause=cause,
            run_log_path=log_dir,
            cwd=cwd,
            state=state,
        )
        return 2

    if _commit_subject_exists(
        subject,
        cwd=cwd,
        base_branch=config.base_branch,
        existing_subjects=existing_fix_subjects,
    ):
        _check_call_with_heartbeat(
            ["git", "push"],
            cwd=cwd,
            heartbeat=state.heartbeat,
            state=state,
        )
        state.write(
            phase="review",
            progress={
                "message": "review fix commit already exists",
                "review_round": round_index,
                "commit_subject": subject,
            },
        )
        return 1

    set_issue_state(
        issue_ref,
        current_labels=("sympohy:running", "sympohy:phase:review"),
        status="sympohy:running",
        phase="fix",
        cwd=cwd,
    )
    fix_log_path = log_dir / f"fix-{round_index}.log"
    state.write(
        phase="fix",
        progress={
            "message": "fixing blocking review findings",
            "review_round": round_index,
            "blocking_findings": len(review.blocking_findings),
            "log_path": str(fix_log_path),
        },
    )
    _codex_text(
        [
            "Fix these blocking review findings and stop after edits.",
            review_json,
        ],
        cwd=cwd,
        log_path=fix_log_path,
        heartbeat=state.heartbeat,
        config=config,
        role="fix",
        state=state,
    )
    if not _worktree_has_changes(cwd):
        state.write(
            phase="review",
            progress={
                "message": "review fix produced no local changes; rerunning review",
                "review_round": round_index,
                "commit_subject": subject,
            },
        )
        return 1

    committed = _commit_all_if_new(
        subject,
        cwd=cwd,
        base_branch=config.base_branch,
        existing_subjects=existing_fix_subjects,
    )
    if committed:
        _check_call_with_heartbeat(
            ["git", "push"],
            cwd=cwd,
            heartbeat=state.heartbeat,
            state=state,
        )
    state.write(
        phase="review",
        progress={
            "message": "pushed review fix" if committed else "review fix commit already exists",
            "review_round": round_index,
            "commit_subject": subject,
        },
    )
    return 1


def _resume_fix_phase(
    issue_ref: str,
    issue: Issue,
    config: SympohyConfig,
    cwd: Path,
    log_dir: Path,
    state: _RunStateWriter,
    *,
    previous_state: Mapping[str, object] | None,
) -> int:
    if _last_progress(previous_state).get("fix_source") == "final_verifier":
        return _resume_final_verifier_fix_phase(
            issue_ref,
            issue,
            config,
            cwd,
            log_dir,
            state,
            previous_state=previous_state,
        )

    round_index = _progress_int(previous_state, "review_round")
    if round_index is None:
        _block(
            issue_ref,
            phase="fix",
            failed_command="resume safety check",
            attempts=1,
            cause="saved fix phase is missing review_round",
            run_log_path=log_dir,
            cwd=cwd,
            state=state,
        )
        return 2
    review_log_path = log_dir / f"review-{round_index}.json"
    try:
        review_json = review_log_path.read_text(encoding="utf-8")
        review = parse_review_json(review_json)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        _block(
            issue_ref,
            phase="fix",
            failed_command="resume safety check",
            attempts=1,
            cause=f"could not load review findings from {review_log_path}: {exc}",
            run_log_path=log_dir,
            cwd=cwd,
            state=state,
        )
        return 2

    existing_fix_subjects = set(_commit_subjects(cwd=cwd, base_branch=config.base_branch))
    review_result = _run_review_fix_round(
        issue_ref,
        issue,
        config,
        cwd,
        log_dir,
        state,
        round_index=round_index,
        review=review,
        review_json=review_json,
        review_pull_request="",
        comment_review=False,
        existing_fix_subjects=existing_fix_subjects,
    )

    if review_result == 1:
        pull_request_number = _resolve_pull_request_number(cwd)
        return _review_fix_loop(
            issue_ref,
            issue,
            config,
            cwd,
            log_dir,
            state,
            start_round=round_index + 1,
            pull_request_number=pull_request_number,
            existing_fix_subjects=existing_fix_subjects,
        )
    return review_result


def _resume_final_verifier_fix_phase(
    issue_ref: str,
    issue: Issue,
    config: SympohyConfig,
    cwd: Path,
    log_dir: Path,
    state: _RunStateWriter,
    *,
    previous_state: Mapping[str, object] | None,
) -> int:
    fix_attempt = _progress_int(previous_state, "final_verifier_fix_attempt")
    if fix_attempt is None or fix_attempt < 1:
        _block(
            issue_ref,
            phase="fix",
            failed_command="resume safety check",
            attempts=1,
            cause="saved final verifier fix phase is missing final_verifier_fix_attempt",
            run_log_path=log_dir,
            cwd=cwd,
            state=state,
        )
        return 2

    final_verifier_log_path = _final_verifier_log_path(log_dir, fix_attempt)
    try:
        final_verifier = json.loads(
            final_verifier_log_path.read_text(encoding="utf-8")
        )
        findings = parse_final_verifier_block_findings(final_verifier)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        _block(
            issue_ref,
            phase="fix",
            failed_command="resume safety check",
            attempts=1,
            cause=(
                "could not load final verifier findings from "
                f"{final_verifier_log_path}: {exc}"
            ),
            run_log_path=log_dir,
            cwd=cwd,
            state=state,
        )
        return 2

    fix_result = _run_final_verifier_fix_round(
        issue_ref,
        issue,
        config,
        cwd,
        log_dir,
        state,
        findings=findings,
        fix_attempt=fix_attempt,
        total_steps=_progress_int(previous_state, "total_logical_steps"),
        from_resume=True,
    )
    if fix_result == 1:
        return _review_fix_loop(
            issue_ref,
            issue,
            config,
            cwd,
            log_dir,
            state,
            start_round=_next_review_rerun_round(
                log_dir,
                max_review_rounds=config.review_max_rounds,
            ),
            block_phase="finalize",
        )
    return fix_result


def _block_dirty_late_phase_resume(
    issue_ref: str,
    *,
    resume_from: str,
    worktree: Path,
    log_dir: Path,
    state: _RunStateWriter,
) -> int | None:
    try:
        status = _worktree_status(worktree)
    except subprocess.CalledProcessError:
        cause = f"could not inspect worktree status for {worktree}"
    else:
        if not status.strip():
            return None
        cause = (
            f"{resume_from} phase worktree has uncommitted changes during resume: "
            f"{_summarize_status(status)}"
        )
    state.record_recovery(
        "unsafe_recovery_blocked",
        {
            "cause": cause,
            "resume_point": resume_from,
        },
    )
    _block(
        issue_ref,
        phase=resume_from,
        failed_command="resume safety check",
        attempts=1,
        cause=cause,
        run_log_path=log_dir,
        cwd=worktree,
        state=state,
        current_labels=("sympohy:running", f"sympohy:phase:{resume_from}"),
    )
    return 2


def _run_final_verifier_and_merge(
    issue_ref: str,
    issue: Issue,
    config: SympohyConfig,
    worktree: Path,
    log_dir: Path,
    state: _RunStateWriter,
    *,
    total_steps: int | None,
) -> int:
    if _pull_request_merged(cwd=worktree):
        return _finish_merged_issue(
            issue_ref,
            worktree,
            state,
            total_steps=total_steps,
            message="reconciled already-merged pull request",
        )

    empty_review = parse_review_json('{"findings":[]}')
    pull_request_number = _resolve_pull_request_number(worktree)
    state.write(
        phase="finalize",
        progress={"message": "capturing browser observation"},
    )
    _record_browser_observation_boundary(state=state, log_dir=log_dir)
    verifier_attempt = 0
    while True:
        verifier_attempt += 1
        final_verifier_path = _final_verifier_log_path(log_dir, verifier_attempt)
        progress: dict[str, object] = {
            "message": "running final verifier",
            "log_path": str(final_verifier_path),
            "final_verifier_attempt": verifier_attempt,
        }
        if total_steps is not None:
            progress["completed_logical_steps"] = total_steps
            progress["total_logical_steps"] = total_steps
        state.write(phase="finalize", progress=progress)
        final = _codex_json(
            [
                FINAL_VERIFIER_PROMPT,
                f"Issue #{issue.number}",
            ],
            cwd=worktree,
            log_path=final_verifier_path,
            heartbeat=state.heartbeat,
            config=config,
            role="merge_readiness",
            state=state,
        )
        final = _final_verifier_with_stage_status(final)
        _persist_final_verifier_artifacts(log_dir, final_verifier_path, final)
        _comment_final_verifier_result(
            pull_request_number,
            final_verifier_path,
            final,
            cwd=worktree,
        )
        if merge_gate_allows_merge(
            final_verifier=final,
            github_checks_status="success",
            review_result=empty_review,
        ):
            if not _stage_gate_passed(
                "merge",
                config=config,
                issue_ref=issue_ref,
                issue=issue,
                log_dir=log_dir,
                context={
                    "acceptance_criteria_satisfied": True,
                    "definition_of_done_satisfied": True,
                    "ci_passed": True,
                    "review_approved": True,
                    "final_verifier_log_path": str(final_verifier_path),
                },
                phase="finalize",
                cwd=worktree,
                state=state,
                current_labels=("sympohy:running", "sympohy:phase:finalize"),
            ):
                return 2
            break

        recommendation = str(final.get("merge_recommendation", "")).lower()
        if recommendation != "block":
            _block(
                issue_ref,
                phase="finalize",
                failed_command="final verifier",
                attempts=verifier_attempt,
                cause="final verifier did not recommend merge or block",
                run_log_path=log_dir,
                cwd=worktree,
                state=state,
            )
            return 2
        if str(final.get("status", "")).lower() == "block":
            _block(
                issue_ref,
                phase="finalize",
                failed_command="final verifier",
                attempts=verifier_attempt,
                cause="final verifier requested manual block",
                run_log_path=log_dir,
                cwd=worktree,
                state=state,
            )
            return 2
        try:
            findings = parse_final_verifier_block_findings(final)
        except ValueError as exc:
            _block(
                issue_ref,
                phase="finalize",
                failed_command="final verifier",
                attempts=verifier_attempt,
                cause=f"final verifier block response has invalid findings: {exc}",
                run_log_path=log_dir,
                cwd=worktree,
                state=state,
            )
            return 2
        fix_attempt = verifier_attempt
        if fix_attempt > config.final_verifier_fix_max_attempts:
            _block(
                issue_ref,
                phase="finalize",
                failed_command="final verifier",
                attempts=fix_attempt,
                cause=(
                    "final verifier findings exceeded "
                    "final_verifier_fix_max_attempts "
                    f"({config.final_verifier_fix_max_attempts})"
                ),
                run_log_path=log_dir,
                cwd=worktree,
                state=state,
            )
            return 2
        fix_result = _run_final_verifier_fix_round(
            issue_ref,
            issue,
            config,
            worktree,
            log_dir,
            state,
            findings=findings,
            fix_attempt=fix_attempt,
            total_steps=total_steps,
        )
        if fix_result != 1:
            return fix_result
        review_result = _review_fix_loop(
            issue_ref,
            issue,
            config,
            worktree,
            log_dir,
            state,
            start_round=_next_review_rerun_round(
                log_dir,
                max_review_rounds=config.review_max_rounds,
            ),
            block_phase="finalize",
        )
        if review_result != 0:
            return review_result

    merge_progress: dict[str, object] = {"message": "merging pull request"}
    if total_steps is not None:
        merge_progress["completed_logical_steps"] = total_steps
        merge_progress["total_logical_steps"] = total_steps
    state.write(phase="finalize", progress=merge_progress)
    _check_call_with_heartbeat(
        ["gh", "pr", "ready"],
        cwd=worktree,
        heartbeat=state.heartbeat,
        state=state,
    )
    _check_call_with_heartbeat(
        ["gh", "pr", "checks", "--watch"],
        cwd=worktree,
        heartbeat=state.heartbeat,
        state=state,
    )
    _check_call_with_heartbeat(
        ["gh", "pr", "merge", "--squash", "--delete-branch"],
        cwd=worktree,
        heartbeat=state.heartbeat,
        state=state,
    )
    return _finish_merged_issue(
        issue_ref,
        worktree,
        state,
        total_steps=total_steps,
        message="merged pull request and removed worktree",
    )


def _final_verifier_log_path(log_dir: Path, attempt: int) -> Path:
    return log_dir / f"final-verifier-{attempt}.json"


def _final_verifier_with_stage_status(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    result = dict(payload)
    status = str(result.get("status", "")).lower()
    if status not in {"pass", "retry", "block"}:
        recommendation = str(result.get("merge_recommendation", "")).lower()
        status = "pass" if recommendation == "merge" else "retry"
    result["status"] = status
    return result


def _persist_final_verifier_artifacts(
    log_dir: Path,
    attempt_path: Path,
    payload: Mapping[str, object],
) -> None:
    latest_path = log_dir / "final-verifier.json"
    content = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    attempt_path.write_bytes(content)
    latest_path.write_bytes(content)


def _comment_final_verifier_result(
    pull_request_number: str,
    attempt_path: Path,
    payload: Mapping[str, object],
    *,
    cwd: Path,
) -> None:
    if attempt_path.exists():
        content = attempt_path.read_text(encoding="utf-8")
    else:
        content = (
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )
    body = (
        "sympohy final verifier result.\n\n"
        f"- log: {attempt_path.name}\n\n"
        "```json\n"
        f"{content.rstrip()}\n"
        "```\n"
    )
    comment(pull_request_number, body, cwd=cwd)


def _run_final_verifier_fix_round(
    issue_ref: str,
    issue: Issue,
    config: SympohyConfig,
    cwd: Path,
    log_dir: Path,
    state: _RunStateWriter,
    *,
    findings: Sequence[FinalVerifierFinding],
    fix_attempt: int,
    total_steps: int | None,
    existing_fix_subjects: set[str] | None = None,
    from_resume: bool = False,
) -> int:
    subject = _final_verifier_fix_subject(issue.number, fix_attempt)
    if _worktree_has_changes(cwd):
        cause = (
            "final verifier fix phase worktree has uncommitted changes"
            f"{' during resume' if from_resume else ''}: "
            f"{_summarize_status(_worktree_status(cwd))}"
        )
        if from_resume:
            state.record_recovery(
                "unsafe_recovery_blocked",
                {
                    "cause": cause,
                    "resume_point": "fix",
                    "fix_source": "final_verifier",
                    "final_verifier_fix_attempt": fix_attempt,
                },
            )
        _block(
            issue_ref,
            phase="fix",
            failed_command="final verifier fix safety check",
            attempts=fix_attempt,
            cause=cause,
            run_log_path=log_dir,
            cwd=cwd,
            state=state,
        )
        return 2

    if _commit_subject_exists(
        subject,
        cwd=cwd,
        base_branch=config.base_branch,
        existing_subjects=existing_fix_subjects,
    ):
        if _run_preflight_validations(
            config.ci_retry_max_attempts,
            cwd,
            log_dir,
            config=config,
            state=state,
        ) != 0:
            _block(
                issue_ref,
                phase="hooks",
                failed_command="scoped validation",
                attempts=config.ci_retry_max_attempts,
                cause="scoped validation still failed after final verifier fix retries",
                run_log_path=log_dir,
                cwd=cwd,
                state=state,
            )
            return 2
        if _run_hooks(
            config.hooks,
            config.ci_retry_max_attempts,
            cwd,
            log_dir,
            config=config,
            state=state,
        ) != 0:
            _block(
                issue_ref,
                phase="hooks",
                failed_command="; ".join(config.hooks),
                attempts=config.ci_retry_max_attempts,
                cause="verification hooks still failed after final verifier fix",
                run_log_path=log_dir,
                cwd=cwd,
                state=state,
            )
            return 2
        _check_call_with_heartbeat(
            ["git", "push"],
            cwd=cwd,
            heartbeat=state.heartbeat,
            state=state,
        )
        state.write(
            phase="finalize",
            progress={
                "message": "final verifier fix commit already exists",
                "fix_source": "final_verifier",
                "final_verifier_fix_attempt": fix_attempt,
                "commit_subject": subject,
            },
        )
        return 1

    set_issue_state(
        issue_ref,
        current_labels=(),
        status="sympohy:running",
        phase="fix",
        cwd=cwd,
    )
    fix_log_path = log_dir / f"final-verifier-fix-{fix_attempt}.log"
    findings_payload = [
        {
            "kind": finding.kind,
            "summary": finding.summary,
            "evidence": finding.evidence,
            "suggested_fix": finding.suggested_fix,
        }
        for finding in findings
    ]
    progress: dict[str, object] = {
        "message": "fixing final verifier findings",
        "fix_source": "final_verifier",
        "final_verifier_fix_attempt": fix_attempt,
        "blocking_findings": len(findings),
        "log_path": str(fix_log_path),
    }
    if total_steps is not None:
        progress["completed_logical_steps"] = total_steps
        progress["total_logical_steps"] = total_steps
    state.write(phase="fix", progress=progress)
    _codex_text(
        [
            "Fix these final verifier findings and stop after edits.",
            json.dumps({"findings": findings_payload}, ensure_ascii=False),
        ],
        cwd=cwd,
        log_path=fix_log_path,
        heartbeat=state.heartbeat,
        config=config,
        role="fix",
        state=state,
    )

    if not _worktree_has_changes(cwd):
        _block(
            issue_ref,
            phase="fix",
            failed_command="final verifier fix",
            attempts=fix_attempt,
            cause=(
                "final verifier fix produced no changes for commit subject: "
                f"{subject}"
            ),
            run_log_path=log_dir,
            cwd=cwd,
            state=state,
        )
        return 2

    if _run_preflight_validations(
        config.ci_retry_max_attempts,
        cwd,
        log_dir,
        config=config,
        state=state,
    ) != 0:
        _block(
            issue_ref,
            phase="hooks",
            failed_command="scoped validation",
            attempts=config.ci_retry_max_attempts,
            cause="scoped validation still failed after final verifier fix retries",
            run_log_path=log_dir,
            cwd=cwd,
            state=state,
        )
        return 2

    if _run_hooks(
        config.hooks,
        config.ci_retry_max_attempts,
        cwd,
        log_dir,
        config=config,
        state=state,
    ) != 0:
        _block(
            issue_ref,
            phase="hooks",
            failed_command="; ".join(config.hooks),
            attempts=config.ci_retry_max_attempts,
            cause="verification hooks still failed after final verifier fix",
            run_log_path=log_dir,
            cwd=cwd,
            state=state,
        )
        return 2

    committed = _commit_all_if_new(
        subject,
        cwd=cwd,
        base_branch=config.base_branch,
        existing_subjects=existing_fix_subjects,
    )
    if committed:
        _check_call_with_heartbeat(
            ["git", "push"],
            cwd=cwd,
            heartbeat=state.heartbeat,
            state=state,
        )
    state.write(
        phase="finalize",
        progress={
            "message": "pushed final verifier fix"
            if committed
            else "final verifier fix commit already exists",
            "fix_source": "final_verifier",
            "final_verifier_fix_attempt": fix_attempt,
            "commit_subject": subject,
        },
    )
    return 1


def _final_verifier_fix_subject(issue_number: int, fix_attempt: int) -> str:
    subject = (
        f"#{issue_number} fix(sympohy): "
        f"resolve final verifier finding {fix_attempt}"
    )
    if not validate_commit_subject(subject):
        raise ValueError(f"invalid generated commit subject: {subject}")
    return subject


def _finish_merged_issue(
    issue_ref: str,
    worktree: Path,
    state: _RunStateWriter,
    *,
    total_steps: int | None,
    message: str,
) -> int:
    if worktree.exists():
        _check_call_with_heartbeat(
            ["git", "worktree", "remove", str(worktree)],
            cwd=Path.cwd(),
            heartbeat=state.heartbeat,
            state=state,
        )
    done_progress: dict[str, object] = {"message": message}
    if total_steps is not None:
        done_progress["completed_logical_steps"] = total_steps
        done_progress["total_logical_steps"] = total_steps
    state.write(
        phase="finalize",
        status="done",
        progress=done_progress,
    )
    set_issue_state(
        issue_ref,
        current_labels=("sympohy:running", "sympohy:phase:finalize"),
        status="sympohy:done",
        phase="finalize",
    )
    _check_call_with_heartbeat(
        ["gh", "issue", "close", issue_ref],
        cwd=Path.cwd(),
        heartbeat=state.heartbeat,
        state=state,
    )
    return 0


def _run_hooks(
    hooks: Iterable[str],
    retry_max_attempts: int,
    cwd: Path,
    log_dir: Path,
    *,
    config: SympohyConfig | None = None,
    state: _RunStateWriter | None = None,
    logical_step: int | None = None,
    total_logical_steps: int | None = None,
) -> int:
    for hook_index, command in enumerate(hooks, start=1):
        attempts = 0
        while True:
            attempts += 1
            log_path = log_dir / f"hook-{hook_index}-{attempts}.log"
            if state is not None:
                progress: dict[str, object] = {
                    "message": "running verification hook",
                    "hook": command,
                    "attempt": attempts,
                    "log_path": str(log_path),
                }
                if logical_step is not None:
                    progress["current_logical_step"] = logical_step
                    progress["completed_logical_steps"] = logical_step
                if total_logical_steps is not None:
                    progress["total_logical_steps"] = total_logical_steps
                state.write(phase="hooks", progress=progress)
            started_at = time.monotonic()
            with log_path.open("w", encoding="utf-8") as log:
                returncode = _run_command_with_heartbeat(
                    shlex.split(command),
                    cwd=cwd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    heartbeat=state.heartbeat if state is not None else None,
                )
            if state is not None:
                failure_summary = ""
                test_failures: list[dict[str, object]] = []
                if returncode != 0:
                    hook_output = log_path.read_text(encoding="utf-8")
                    failure_summary = _failure_summary(hook_output)
                    test_failures = _extract_test_failures(hook_output)
                metadata: dict[str, object] = {
                    "command": command,
                    "hook_index": hook_index,
                    "returncode": returncode,
                    "failure_summary": failure_summary,
                }
                if test_failures:
                    metadata["test_failures"] = test_failures
                state.record_event(
                    event_type="hook",
                    status="success" if returncode == 0 else "retry",
                    summary=f"hook {'passed' if returncode == 0 else 'failed'}: {command}",
                    attempt=attempts,
                    duration=_elapsed_seconds(started_at),
                    metadata=metadata,
                )
            if returncode == 0:
                break
            if next_retry_action(attempts, retry_max_attempts) == "block":
                return returncode
            _codex_text(
                [
                    f"The hook failed: {command}",
                    f"Inspect {log_path} and fix the cause, then stop.",
                ],
                cwd=cwd,
                log_path=log_dir / f"hook-fix-{hook_index}-{attempts}.log",
                heartbeat=state.heartbeat if state is not None else None,
                config=config if state is not None else None,
                role="fix",
                state=state,
            )
    return 0


def _changed_worktree_paths(cwd: Path) -> list[str]:
    seen: set[str] = set()
    paths: list[str] = []
    try:
        status_output = _worktree_status(cwd)
    except subprocess.CalledProcessError:
        return paths
    for line in status_output.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[-1].strip()
        if not path:
            continue
        if path in seen:
            continue
        seen.add(path)
        paths.append(path)
    return paths


def _preflight_validation_commands(changed_paths: Sequence[str]) -> list[str]:
    commands: list[str] = []

    def add(command: str) -> None:
        if command not in commands:
            commands.append(command)

    has_frontend_changes = False
    has_python_changes = False
    needs_generic_pytest = False

    python_test_commands = (
        (
            ("scripts/sympohy/runner.py", "tests/sympohy/sympohy_runner_test.py"),
            "task pytest -- tests/sympohy/sympohy_runner_test.py",
        ),
        (
            (
                "scripts/sympohy/observability.py",
                "tests/sympohy/sympohy_observability_test.py",
                "tests/sympohy/fixtures/observability_replay_issue_126.jsonl",
            ),
            "task pytest -- tests/sympohy/sympohy_observability_test.py",
        ),
        (
            ("scripts/sympohy/stage_gate.py", "tests/sympohy/sympohy_stage_gate_test.py"),
            "task pytest -- tests/sympohy/sympohy_stage_gate_test.py",
        ),
        (
            ("scripts/sympohy/config.py", "tests/sympohy/sympohy_config_test.py"),
            "task pytest -- tests/sympohy/sympohy_config_test.py",
        ),
        (
            ("scripts/sympohy/core.py", "tests/sympohy/sympohy_core_test.py"),
            "task pytest -- tests/sympohy/sympohy_core_test.py",
        ),
        (
            (
                "scripts/sympohy/github.py",
                "tests/sympohy/sympohy_github_test.py",
            ),
            "task pytest -- tests/sympohy/sympohy_github_test.py",
        ),
    )

    for path in changed_paths:
        if path.endswith(".md"):
            add("task ci:markdown")
        if path.startswith(("docs/adr/", "docs/design/", "docs/requirements/", "docs/wireframes/")):
            add("task codd:validate")
        if path in {"Taskfile.yml", ".github/workflows/ci.yml"}:
            add("task ci:lint:task-refs")
        if path in {"Taskfile.yml", ".codex/rules/siftq.rules"}:
            add("task ci:lint:codex-task-perms")
        if path.endswith((".ts", ".tsx", ".js", ".jsx", ".css", ".html")) or path.startswith(
            ("src/", "tests/docs/")
        ):
            has_frontend_changes = True
        if path.endswith(".py") or path.startswith("tests/sympohy/"):
            has_python_changes = True
            matched_python_test = False
            for prefixes, command in python_test_commands:
                if any(path.startswith(prefix) for prefix in prefixes):
                    add(command)
                    matched_python_test = True
                    break
            if not matched_python_test and (
                path.startswith("scripts/sympohy/") or path.startswith("tests/sympohy/")
            ):
                needs_generic_pytest = True

    if has_frontend_changes:
        add("task ci:typecheck")
        add("task ci:lint")
        add("task ci:test")
        add("task ci:build")
    if has_python_changes and needs_generic_pytest:
        add("task pytest")
    return commands


def _run_preflight_validations(
    retry_max_attempts: int,
    cwd: Path,
    log_dir: Path,
    *,
    config: SympohyConfig | None = None,
    state: _RunStateWriter | None = None,
    logical_step: int | None = None,
    total_logical_steps: int | None = None,
) -> int:
    commands = _preflight_validation_commands(_changed_worktree_paths(cwd))
    if not commands:
        return 0
    return _run_hooks(
        commands,
        retry_max_attempts,
        cwd,
        log_dir,
        config=config,
        state=state,
        logical_step=logical_step,
        total_logical_steps=total_logical_steps,
    )


def _review_fix_loop(
    issue_ref: str,
    issue: Issue,
    config: SympohyConfig,
    cwd: Path,
    log_dir: Path,
    state: _RunStateWriter,
    *,
    start_round: int = 1,
    pull_request_number: str | None = None,
    existing_fix_subjects: set[str] | None = None,
    block_phase: str = "review",
) -> int:
    if start_round > config.review_max_rounds + 1:
        return 0
    pull_request_number = _ensure_review_mergeability(
        issue_ref,
        issue,
        config,
        cwd,
        log_dir,
        state,
        phase=block_phase,
    )
    if pull_request_number is None:
        return 2
    if existing_fix_subjects is None:
        existing_fix_subjects = set(
            _commit_subjects(cwd=cwd, base_branch=config.base_branch)
        )
    for round_index in range(start_round, config.review_max_rounds + 2):
        set_issue_state(
            issue_ref,
            current_labels=("sympohy:running", "sympohy:phase:review"),
            status="sympohy:running",
            phase="review",
            cwd=cwd,
        )
        review_log_path = log_dir / f"review-{round_index}.json"
        state.write(
            phase="review",
            progress={
                "message": "running adversarial review",
                "review_round": round_index,
                "max_review_rounds": config.review_max_rounds,
                "log_path": str(review_log_path),
            },
        )
        review_json = _codex_text(
            [
                "Review this PR adversarially. Return machine-parseable JSON "
                "with status set to pass or retry and findings: "
                "[{severity, summary, status}]. Use status pass only when there "
                "are no critical/high/medium findings. Use status retry when "
                "critical/high/medium findings remain. Severities are "
                "critical, high, medium, low, info.",
                f"Issue #{issue.number}",
            ],
            cwd=cwd,
            log_path=review_log_path,
            heartbeat=state.heartbeat,
            config=config,
            role="review",
            state=state,
        )
        review = parse_review_json(review_json)
        review_json = _review_json_with_stage_status(review)
        review_log_path.write_text(review_json, encoding="utf-8")
        state.record_event(
            event_type="review",
            status=review.stage_gate_status,
            summary=f"review round {round_index} {review.stage_gate_status}",
            attempt=round_index,
            metadata={
                "reviewer_role": "adversarial-review",
                "review_round": round_index,
                "blocking_findings_summary": _summarize_review_findings(
                    review.blocking_findings
                ),
                "finding_count": len(review.findings),
            },
        )
        review_result = _run_review_fix_round(
            issue_ref,
            issue,
            config,
            cwd,
            log_dir,
            state,
            round_index=round_index,
            review=review,
            review_json=review_json,
            review_pull_request=pull_request_number,
            comment_review=True,
            existing_fix_subjects=existing_fix_subjects,
        )
        if review_result != 1:
            return review_result
    return 2


def _ensure_review_mergeability(
    issue_ref: str,
    issue: Issue,
    config: SympohyConfig,
    cwd: Path,
    log_dir: Path,
    state: _RunStateWriter,
    *,
    phase: str,
) -> str | None:
    mergeability = _pull_request_mergeability(cwd)
    if not mergeability.is_conflicted():
        return mergeability.number

    autofix_log_path = log_dir / "mergeability-autofix.log"
    auto_fix_error = _attempt_pre_review_mergeability_autofix(
        issue_ref,
        issue,
        config,
        cwd,
        log_dir,
        state,
        phase=phase,
        pull_request=mergeability,
        log_path=autofix_log_path,
    )
    if auto_fix_error is None:
        mergeability = _pull_request_mergeability(cwd)
        if not mergeability.is_conflicted():
            return mergeability.number

    recommended_action = (
        "sympohy attempted one pre-review auto-merge/auto-fix pass but the pull "
        "request still conflicts. Update "
        f"`{mergeability.head_ref}` with the latest `{mergeability.base_ref}`, "
        "resolve the merge conflicts, run `task ci`, push the branch, and rerun "
        f"`task ai:sympohy:resume -- '#{issue.number}'`."
    )
    if auto_fix_error is not None:
        recommended_action += f" Last automatic attempt failed: {auto_fix_error}."
    _block_mergeability_conflict(
        issue_ref,
        phase=phase,
        issue_number=issue.number,
        pull_request=mergeability,
        run_log_path=autofix_log_path,
        cwd=cwd,
        state=state,
        recommended_action=recommended_action,
    )
    return None


def _attempt_pre_review_mergeability_autofix(
    issue_ref: str,
    issue: Issue,
    config: SympohyConfig,
    cwd: Path,
    log_dir: Path,
    state: _RunStateWriter,
    *,
    phase: str,
    pull_request: _PullRequestMergeability,
    log_path: Path,
) -> str | None:
    try:
        status = _worktree_status(cwd)
    except subprocess.CalledProcessError as exc:
        return (
            "could not inspect worktree status before automatic conflict fix: "
            f"exit code {exc.returncode}"
        )
    if status.strip():
        return (
            "worktree has uncommitted changes before automatic conflict fix: "
            f"{_summarize_status(status)}"
        )

    merge_target = f"origin/{pull_request.base_ref}"
    merge_subject = _mergeability_autofix_subject(
        issue_number=issue.number,
        base_ref=pull_request.base_ref,
    )
    state.write(
        phase=phase,
        progress={
            "message": "attempting pre-review mergeability auto-fix",
            "failed_command": "mergeability gate",
            "attempts": 1,
            "pull_request_number": pull_request.number,
            "base_ref": pull_request.base_ref,
            "head_ref": pull_request.head_ref,
            "log_path": str(log_path),
        },
    )
    try:
        _check_call_with_heartbeat(
            ["git", "fetch", "origin", pull_request.base_ref],
            cwd=cwd,
            heartbeat=state.heartbeat,
            state=state,
        )
    except subprocess.CalledProcessError as exc:
        return f"git fetch failed with exit code {exc.returncode}"

    merge_command = ["git", "merge", "--no-ff", "--no-commit", merge_target]
    merge_started_at = time.monotonic()
    merge_returncode = _run_command_with_heartbeat(
        merge_command,
        cwd=cwd,
        heartbeat=state.heartbeat,
    )
    _record_command_event(
        state=state,
        args=merge_command,
        status="success" if merge_returncode == 0 else "failed",
        duration=_elapsed_seconds(merge_started_at),
        returncode=merge_returncode,
    )
    if merge_returncode not in {0, 1}:
        return f"git merge exited with unexpected status {merge_returncode}"

    if _merge_has_unmerged_paths(cwd):
        _codex_text(
            [
                "Resolve this pre-review merge conflict introduced by syncing the "
                f"current branch with `{merge_target}`.",
                "Remove all conflict markers, keep the branch mergeable, and stop "
                "after edits.",
                f"Issue #{issue.number}",
            ],
            cwd=cwd,
            log_path=log_path,
            heartbeat=state.heartbeat,
            config=config,
            role="fix",
            state=state,
        )

    if _worktree_has_conflict_markers(cwd):
        return "conflict markers remain after automatic conflict fix"
    subprocess.check_call(["git", "add", "-A"], cwd=cwd)
    if _merge_has_unmerged_paths(cwd):
        return "unmerged paths remain after staging automatic conflict fix"
    if _run_hooks(
        config.hooks,
        config.ci_retry_max_attempts,
        cwd,
        log_dir,
        config=config,
        state=state,
    ) != 0:
        return "task ci failed after automatic conflict fix"

    subprocess.check_call(["git", "add", "-A"], cwd=cwd)
    if _merge_has_unmerged_paths(cwd):
        return "unmerged paths remain after staging automatic conflict fix"
    if _worktree_has_conflict_markers(cwd):
        return "conflict markers remain after staging automatic conflict fix"
    try:
        subprocess.check_call(["git", "commit", "-m", merge_subject], cwd=cwd)
    except subprocess.CalledProcessError as exc:
        return f"git commit failed with exit code {exc.returncode}"
    try:
        _check_call_with_heartbeat(
            ["git", "push"],
            cwd=cwd,
            heartbeat=state.heartbeat,
            state=state,
        )
    except subprocess.CalledProcessError as exc:
        return f"git push failed with exit code {exc.returncode}"

    state.write(
        phase=phase,
        progress={
            "message": "completed pre-review mergeability auto-fix",
            "pull_request_number": pull_request.number,
            "base_ref": pull_request.base_ref,
            "head_ref": pull_request.head_ref,
            "commit_subject": merge_subject,
            "log_path": str(log_path),
        },
    )
    return None


def _mergeability_autofix_subject(*, issue_number: int, base_ref: str) -> str:
    subject = f"#{issue_number} fix(sympohy): sync {base_ref} before review"
    if not validate_commit_subject(subject):
        raise ValueError(f"invalid generated commit subject: {subject}")
    return subject


def _pull_request_mergeability(cwd: Path) -> _PullRequestMergeability:
    payload = json.loads(
        subprocess.check_output(
            [
                "gh",
                "pr",
                "view",
                "--json",
                "number,baseRefName,headRefName,mergeStateStatus,mergeable",
            ],
            cwd=cwd,
            text=True,
        )
    )
    if not isinstance(payload, Mapping):
        raise ValueError("gh pr view returned non-object JSON")
    return _PullRequestMergeability(
        number=str(payload.get("number", "")).strip(),
        base_ref=str(payload.get("baseRefName", "")).strip(),
        head_ref=str(payload.get("headRefName", "")).strip(),
        merge_state_status=str(payload.get("mergeStateStatus", "UNKNOWN")).strip().upper(),
        mergeable=str(payload.get("mergeable", "UNKNOWN")).strip().upper(),
    )


def _review_json_with_stage_status(review: ReviewResult) -> str:
    if isinstance(review.raw, Mapping):
        payload: dict[str, object] = dict(review.raw)
    else:
        payload = {"findings": [finding.__dict__ for finding in review.findings]}
    payload["status"] = review.stage_gate_status
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _block(
    issue_ref: str,
    *,
    phase: str,
    failed_command: str,
    attempts: int,
    cause: str,
    run_log_path: Path,
    cwd: Path | None,
    state: _RunStateWriter | None = None,
    current_labels: Sequence[str] | None = None,
    details: Mapping[str, object] | None = None,
) -> None:
    progress: dict[str, object] = {
        "message": "blocked",
        "failed_command": failed_command,
        "attempts": attempts,
        "cause": cause,
        "run_log_path": str(run_log_path),
    }
    if details:
        progress.update(details)
    if state is not None:
        state.write(
            phase=phase,
            status="blocked",
            progress=progress,
        )
        state.record_event(
            event_type="command",
            status="blocked",
            summary=f"blocked: {failed_command}",
            attempt=attempts,
            metadata={
                "command": failed_command,
                "cause": cause,
                "run_log_path": str(run_log_path),
                **dict(details or {}),
            },
        )
    detail_lines = ""
    if details:
        detail_lines = "".join(f"- {key}: {value}\n" for key, value in details.items())
    set_issue_state(
        issue_ref,
        current_labels=current_labels or ("sympohy:running", f"sympohy:phase:{phase}"),
        status="sympohy:blocked",
        phase=phase,
        cwd=cwd,
    )
    comment(
        issue_ref,
        (
            "sympohy blocked this run.\n\n"
            f"- phase: {phase}\n"
            f"- failed command: {failed_command}\n"
            f"- attempts: {attempts}\n"
            f"- cause: {cause}\n"
            f"{detail_lines}"
            f"- run log path: {run_log_path}\n"
        ),
        cwd=cwd,
    )


def _block_mergeability_conflict(
    issue_ref: str,
    *,
    phase: str,
    issue_number: int,
    pull_request: _PullRequestMergeability,
    run_log_path: Path,
    cwd: Path | None,
    state: _RunStateWriter | None,
    recommended_action: str,
) -> None:
    cause = f"pull request conflicts with base branch {pull_request.base_ref}"
    if state is not None:
        state.write(
            phase=phase,
            status="blocked",
            progress={
                "message": "blocked",
                "failed_command": "mergeability gate",
                "attempts": 1,
                "cause": cause,
                "run_log_path": str(run_log_path),
                "pull_request_number": pull_request.number,
                "base_ref": pull_request.base_ref,
                "head_ref": pull_request.head_ref,
                "conflict_summary": pull_request.conflict_summary(),
                "recommended_action": recommended_action,
            },
        )
        state.record_event(
            event_type="command",
            status="blocked",
            summary="blocked: mergeability gate",
            attempt=1,
            metadata={
                "command": "mergeability gate",
                "cause": cause,
                "run_log_path": str(run_log_path),
                "pull_request_number": pull_request.number,
                "base_ref": pull_request.base_ref,
                "head_ref": pull_request.head_ref,
                "conflict_summary": pull_request.conflict_summary(),
                "recommended_action": recommended_action,
            },
        )
    set_issue_state(
        issue_ref,
        current_labels=("sympohy:running", f"sympohy:phase:{phase}"),
        status="sympohy:blocked",
        phase=phase,
        cwd=cwd,
    )
    comment(
        issue_ref,
        (
            "sympohy blocked this run.\n\n"
            f"- phase: {phase}\n"
            "- failed command: mergeability gate\n"
            "- attempts: 1\n"
            f"- cause: {cause}\n"
            f"- pr number: {pull_request.number}\n"
            f"- base ref: {pull_request.base_ref}\n"
            f"- head ref: {pull_request.head_ref}\n"
            f"- conflict summary: {pull_request.conflict_summary()}\n"
            f"- recommended next action: {recommended_action}\n"
            f"- run log path: {run_log_path}\n"
        ),
        cwd=cwd,
    )


def _codex_json(
    prompts: Sequence[str],
    *,
    cwd: Path,
    log_path: Path,
    heartbeat: Callable[[], None] | None = None,
    config: SympohyConfig | None = None,
    role: str = "default",
    state: _RunStateWriter | None = None,
) -> Mapping[str, object]:
    prompt = "\n\n".join(prompts)
    model_config = config.codex_model_for(role) if config is not None else None
    _record_prompt_instruction_sources(state=state, cwd=cwd, prompt=prompt)
    started_at = time.monotonic()
    try:
        output = _check_output_with_heartbeat(
            _codex_exec_args(prompt, config=config, role=role),
            cwd=cwd,
            heartbeat=heartbeat,
            log_path=log_path,
        )
    except subprocess.CalledProcessError as exc:
        _record_codex_event(
            state=state,
            role=role,
            model=model_config.model if model_config is not None else None,
            reasoning_effort=(
                model_config.reasoning_effort if model_config is not None else None
            ),
            prompt=prompt,
            parse_status="not_attempted",
            duration=_elapsed_seconds(started_at),
            returncode=exc.returncode,
            failure_summary=_failure_summary(exc.output),
        )
        raise

    parse_status = "parsed"
    try:
        payload = json.loads(output)
        if not isinstance(payload, Mapping):
            parse_status = "non_object"
            raise ValueError("Codex JSON output must be an object")
    except json.JSONDecodeError as exc:
        parse_status = "invalid_json"
        _record_codex_event(
            state=state,
            role=role,
            model=model_config.model if model_config is not None else None,
            reasoning_effort=(
                model_config.reasoning_effort if model_config is not None else None
            ),
            prompt=prompt,
            parse_status=parse_status,
            duration=_elapsed_seconds(started_at),
            returncode=0,
            failure_summary=_failure_summary(str(exc)),
        )
        raise
    except ValueError as exc:
        _record_codex_event(
            state=state,
            role=role,
            model=model_config.model if model_config is not None else None,
            reasoning_effort=(
                model_config.reasoning_effort if model_config is not None else None
            ),
            prompt=prompt,
            parse_status=parse_status,
            duration=_elapsed_seconds(started_at),
            returncode=0,
            failure_summary=_failure_summary(str(exc)),
        )
        raise

    _record_codex_event(
        state=state,
        role=role,
        model=model_config.model if model_config is not None else None,
        reasoning_effort=(
            model_config.reasoning_effort if model_config is not None else None
        ),
        prompt=prompt,
        parse_status=parse_status,
        duration=_elapsed_seconds(started_at),
        returncode=0,
        failure_summary="",
    )
    return payload


def _codex_text(
    prompts: Sequence[str],
    *,
    cwd: Path,
    log_path: Path,
    heartbeat: Callable[[], None] | None = None,
    config: SympohyConfig | None = None,
    role: str = "default",
    state: _RunStateWriter | None = None,
) -> str:
    prompt = "\n\n".join(prompts)
    model_config = config.codex_model_for(role) if config is not None else None
    _record_prompt_instruction_sources(state=state, cwd=cwd, prompt=prompt)
    started_at = time.monotonic()
    try:
        output = _check_output_with_heartbeat(
            _codex_exec_args(prompt, config=config, role=role),
            cwd=cwd,
            heartbeat=heartbeat,
            log_path=log_path,
        )
    except subprocess.CalledProcessError as exc:
        _record_codex_event(
            state=state,
            role=role,
            model=model_config.model if model_config is not None else None,
            reasoning_effort=(
                model_config.reasoning_effort if model_config is not None else None
            ),
            prompt=prompt,
            parse_status="not_requested",
            duration=_elapsed_seconds(started_at),
            returncode=exc.returncode,
            failure_summary=_failure_summary(exc.output),
        )
        raise
    _record_codex_event(
        state=state,
        role=role,
        model=model_config.model if model_config is not None else None,
        reasoning_effort=(
            model_config.reasoning_effort if model_config is not None else None
        ),
        prompt=prompt,
        parse_status="not_requested",
        duration=_elapsed_seconds(started_at),
        returncode=0,
        failure_summary="",
    )
    return output


def _codex_exec_args(
    prompt: str,
    *,
    config: SympohyConfig | None,
    role: str,
) -> list[str]:
    args = ["codex", "exec"]
    if config is not None:
        model_config = config.codex_model_for(role)
        args.extend(
            [
                "--model",
                model_config.model,
                "-c",
                f'model_reasoning_effort="{model_config.reasoning_effort}"',
            ]
        )
    args.append(prompt)
    return args


def _check_output_with_heartbeat(
    args: Sequence[str],
    *,
    cwd: Path,
    heartbeat: Callable[[], None] | None = None,
    log_path: Path | None = None,
) -> str:
    process = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE)
    stdout = getattr(process, "stdout", None)
    if stdout is None:
        return _communicate_output_with_heartbeat(
            process,
            args=args,
            heartbeat=heartbeat,
        )
    chunks: list[bytes] = []
    log_file = log_path.open("wb") if log_path is not None else None
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(stdout, selectors.EVENT_READ)
            next_heartbeat_at = time.monotonic() + HEARTBEAT_INTERVAL_SECONDS
            while True:
                timeout = max(0.0, next_heartbeat_at - time.monotonic())
                events = selector.select(timeout=timeout)
                now = time.monotonic()
                if heartbeat is not None and now >= next_heartbeat_at:
                    heartbeat()
                    next_heartbeat_at = now + HEARTBEAT_INTERVAL_SECONDS

                if not events:
                    if process.poll() is not None:
                        while True:
                            data = os.read(stdout.fileno(), 8192)
                            if not data:
                                break
                            chunks.append(data)
                            if log_file is not None:
                                log_file.write(data)
                                log_file.flush()
                        process.wait()
                        output = b"".join(chunks).decode("utf-8", errors="replace")
                        if process.returncode != 0:
                            raise subprocess.CalledProcessError(
                                process.returncode,
                                args,
                                output=output,
                            )
                        return output
                    continue
                for key, _mask in events:
                    data = os.read(key.fileobj.fileno(), 8192)
                    if not data:
                        selector.unregister(key.fileobj)
                        process.wait()
                        output = b"".join(chunks).decode("utf-8", errors="replace")
                        if process.returncode != 0:
                            raise subprocess.CalledProcessError(
                                process.returncode,
                                args,
                                output=output,
                            )
                        return output
                    chunks.append(data)
                    if log_file is not None:
                        log_file.write(data)
                        log_file.flush()
    except Exception:
        _terminate_process(process)
        raise
    finally:
        if log_file is not None:
            log_file.close()


def _communicate_output_with_heartbeat(
    process: subprocess.Popen[bytes],
    *,
    args: Sequence[str],
    heartbeat: Callable[[], None] | None,
) -> str:
    try:
        while True:
            try:
                output, _stderr = process.communicate(
                    timeout=HEARTBEAT_INTERVAL_SECONDS
                )
                break
            except subprocess.TimeoutExpired:
                if heartbeat is not None:
                    heartbeat()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode,
                args,
                output=output,
            )
        if isinstance(output, bytes):
            return output.decode("utf-8", errors="replace")
        return output
    except Exception:
        _terminate_process(process)
        raise


def _run_command_with_heartbeat(
    args: Sequence[str],
    *,
    cwd: Path,
    heartbeat: Callable[[], None] | None = None,
    **popen_kwargs: object,
) -> int:
    process = subprocess.Popen(args, cwd=cwd, **popen_kwargs)
    try:
        while True:
            try:
                return process.wait(timeout=HEARTBEAT_INTERVAL_SECONDS)
            except subprocess.TimeoutExpired:
                if heartbeat is not None:
                    heartbeat()
    except Exception:
        if process.poll() is None:
            _terminate_process(process)
        raise


def _check_call_with_heartbeat(
    args: Sequence[str],
    *,
    cwd: Path,
    heartbeat: Callable[[], None] | None = None,
    state: _RunStateWriter | None = None,
) -> None:
    started_at = time.monotonic()
    returncode: int | None = None
    try:
        returncode = _run_command_with_heartbeat(args, cwd=cwd, heartbeat=heartbeat)
    except Exception as exc:
        _record_command_event(
            state=state,
            args=args,
            status="failed",
            duration=_elapsed_seconds(started_at),
            returncode=returncode,
            failure_summary=str(exc),
        )
        raise
    _record_command_event(
        state=state,
        args=args,
        status="success" if returncode == 0 else "failed",
        duration=_elapsed_seconds(started_at),
        returncode=returncode,
    )
    if returncode != 0:
        raise subprocess.CalledProcessError(returncode, args)


def _record_command_event(
    *,
    state: _RunStateWriter | None,
    args: Sequence[str],
    status: str,
    duration: float | int | None,
    returncode: int | None,
    failure_summary: str = "",
) -> None:
    if state is None:
        return
    command = shlex.join(str(arg) for arg in args)
    metadata: dict[str, object] = {
        "command": command,
        "argv": [str(arg) for arg in args],
    }
    if returncode is not None:
        metadata["returncode"] = returncode
    if failure_summary:
        metadata["failure_summary"] = _failure_summary(failure_summary)
    state.record_event(
        event_type="command",
        status=status,
        summary=f"command {status}: {command}",
        duration=duration,
        metadata=metadata,
    )


def _terminate_process(process: subprocess.Popen[object]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _current_branch(cwd: Path) -> str:
    return subprocess.check_output(
        ["git", "branch", "--show-current"],
        cwd=cwd,
        text=True,
    ).strip()


def _isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _new_run_id() -> str:
    return uuid.uuid4().hex


def _lock_payload(
    *,
    run_id: str,
    issue_number: int,
    phase: str | None,
    heartbeat: str,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "issue": issue_number,
        "pid": os.getpid(),
        "phase": phase,
        "heartbeat": heartbeat,
    }


def _refresh_lock_metadata(
    lock_path: Path,
    *,
    run_id: str,
    issue_number: int,
    phase: str | None,
    heartbeat: str,
) -> None:
    current = read_run_state(lock_path)
    if current is None or current.get("run_id") not in {None, run_id}:
        raise _RunLockedError(f"run {run_id} no longer owns lock {lock_path}")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = lock_path.with_suffix(".lock.tmp")
    tmp_path.write_text(
        json.dumps(
            _lock_payload(
                run_id=run_id,
                issue_number=issue_number,
                phase=phase,
                heartbeat=heartbeat,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(lock_path)


def _lock_takeover_allowed(
    lock_path: Path,
    *,
    state_path: Path,
    issue_number: int,
    stale_status_after_minutes: int,
) -> bool:
    lock_payload = read_run_state(lock_path)
    if lock_payload is None:
        return False
    if lock_payload.get("issue") != issue_number:
        return False

    lock_run_id = lock_payload.get("run_id")
    if not isinstance(lock_run_id, str) or not lock_run_id:
        return False

    state_payload = read_run_state(state_path)
    if state_payload is None:
        return False
    if state_payload.get("issue") != issue_number:
        return False

    state_run_id = state_payload.get("run_id")
    if not isinstance(state_run_id, str) or not state_run_id:
        return False

    state_lock = state_payload.get("lock")
    if isinstance(state_lock, Mapping):
        if state_lock.get("run_id") not in {None, state_run_id}:
            return False
        lock_path_in_state = state_lock.get("path")
        if isinstance(lock_path_in_state, str) and Path(lock_path_in_state) != lock_path:
            return False

    if state_run_id != lock_run_id:
        return False

    if not _payload_process_alive(lock_payload):
        return True
    return not _payload_has_fresh_heartbeat(
        lock_payload,
        stale_status_after_minutes=stale_status_after_minutes,
    ) and not _payload_has_fresh_heartbeat(
        state_payload,
        stale_status_after_minutes=stale_status_after_minutes,
    )


def _lock_process_alive(lock_path: Path) -> bool:
    payload = read_run_state(lock_path)
    if payload is None:
        return False
    return _payload_process_alive(payload)


def _payload_process_alive(payload: Mapping[str, object]) -> bool:
    pid = payload.get("pid")
    if isinstance(pid, bool):
        return False
    if isinstance(pid, str):
        try:
            pid = int(pid)
        except ValueError:
            return False
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _payload_has_fresh_heartbeat(
    payload: Mapping[str, object],
    *,
    stale_status_after_minutes: int,
) -> bool:
    heartbeat = _heartbeat_from_payload(payload)
    if heartbeat is None:
        return False
    stale_after_seconds = stale_status_after_minutes * 60
    age_seconds = (datetime.now(timezone.utc) - heartbeat).total_seconds()
    return age_seconds <= stale_after_seconds


def _heartbeat_from_payload(payload: Mapping[str, object]) -> datetime | None:
    value = payload.get("heartbeat")
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        heartbeat = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if heartbeat.tzinfo is None:
        return heartbeat.replace(tzinfo=timezone.utc)
    return heartbeat.astimezone(timezone.utc)


def _logical_steps(plan: Mapping[str, object]) -> list[Mapping[str, object]]:
    steps = plan.get("logical_steps", [])
    if not isinstance(steps, list) or not steps:
        raise ValueError("plan JSON must contain non-empty logical_steps")
    logical_steps: list[Mapping[str, object]] = []
    for step in steps:
        if isinstance(step, Mapping):
            logical_steps.append(step)
        elif isinstance(step, str) and step.strip():
            logical_steps.append({"description": step.strip()})
    if not logical_steps:
        raise ValueError("plan JSON logical_steps must contain strings or objects")
    return logical_steps


def _load_existing_plan(plan_path: Path) -> Mapping[str, object] | None:
    if not plan_path.exists():
        return None
    try:
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, Mapping):
        return None
    try:
        _logical_steps(payload)
    except ValueError:
        return None
    return payload


def _infer_implementation_recovery(
    issue_number: int,
    *,
    cwd: Path,
    base_branch: str,
    total_steps: int,
) -> _ImplementationRecovery:
    try:
        subjects = _commit_subjects(
            cwd=cwd,
            base_branch=base_branch,
            allow_fallback=False,
        )
    except subprocess.CalledProcessError:
        return _ImplementationRecovery(
            committed_logical_steps=0,
            unsafe_reason=(
                "could not inspect logical step commits relative to "
                f"base branch {base_branch}"
            ),
        )

    committed_steps = _logical_step_numbers_from_commits(issue_number, subjects)
    completed = _contiguous_logical_step_prefix(committed_steps, total_steps)
    inconsistent_steps = sorted(step for step in committed_steps if step > completed)
    if inconsistent_steps:
        return _ImplementationRecovery(
            committed_logical_steps=completed,
            unsafe_reason=(
                "logical step commits are inconsistent; "
                f"completed contiguous prefix is {completed}, "
                f"but found later step commits {inconsistent_steps}"
            ),
        )

    try:
        status = _worktree_status(cwd)
    except subprocess.CalledProcessError:
        return _ImplementationRecovery(
            committed_logical_steps=completed,
            unsafe_reason=f"could not inspect worktree status for {cwd}",
        )
    worktree_clean = not status.strip()
    if not worktree_clean:
        return _ImplementationRecovery(
            committed_logical_steps=completed,
            worktree_clean=False,
            unsafe_reason=(
                "worktree has uncommitted changes during resume: "
                f"{_summarize_status(status)}"
            ),
        )

    return _ImplementationRecovery(
        committed_logical_steps=completed,
        worktree_clean=worktree_clean,
    )


def _completed_logical_steps_from_commits(
    issue_number: int,
    *,
    cwd: Path,
    base_branch: str,
    total_steps: int,
) -> int:
    subjects = _commit_subjects(cwd=cwd, base_branch=base_branch)
    committed_steps = _logical_step_numbers_from_commits(issue_number, subjects)
    return _contiguous_logical_step_prefix(committed_steps, total_steps)


def _logical_step_numbers_from_commits(
    issue_number: int,
    subjects: Iterable[str],
) -> set[int]:
    committed_steps: set[int] = set()
    for subject in subjects:
        match = LOGICAL_STEP_COMMIT_RE.match(subject)
        if match is None or int(match.group("issue")) != issue_number:
            continue
        committed_steps.add(int(match.group("step")))
    return committed_steps


def _contiguous_logical_step_prefix(committed_steps: set[int], total_steps: int) -> int:
    completed = 0
    while completed + 1 in committed_steps and completed < total_steps:
        completed += 1
    return completed


def _commit_subjects(
    *,
    cwd: Path,
    base_branch: str,
    allow_fallback: bool = True,
) -> list[str]:
    try:
        output = subprocess.check_output(
            ["git", "log", "--format=%s", f"{base_branch}..HEAD"],
            cwd=cwd,
            text=True,
        )
    except subprocess.CalledProcessError:
        if not allow_fallback:
            raise
        output = subprocess.check_output(
            ["git", "log", "--format=%s"],
            cwd=cwd,
            text=True,
        )
    return output.splitlines()


def _commit_subject_exists(
    subject: str,
    *,
    cwd: Path,
    base_branch: str,
    existing_subjects: set[str] | None = None,
) -> bool:
    if existing_subjects is not None:
        return subject in existing_subjects
    return subject in _commit_subjects(cwd=cwd, base_branch=base_branch)


def _commit_all_if_new(
    subject: str,
    *,
    cwd: Path,
    base_branch: str,
    allow_empty: bool = False,
    existing_subjects: set[str] | None = None,
) -> bool:
    if _commit_subject_exists(
        subject,
        cwd=cwd,
        base_branch=base_branch,
        existing_subjects=existing_subjects,
    ):
        return False

    subprocess.check_call(["git", "add", "-A"], cwd=cwd)
    if not _worktree_has_changes(cwd):
        if _commit_subject_exists(
            subject,
            cwd=cwd,
            base_branch=base_branch,
            existing_subjects=existing_subjects,
        ):
            return False
        if allow_empty:
            subprocess.check_call(
                ["git", "commit", "--allow-empty", "-m", subject],
                cwd=cwd,
            )
            if existing_subjects is not None:
                existing_subjects.add(subject)
            return True
        raise RuntimeError(f"no changes to commit for subject: {subject}")

    subprocess.check_call(["git", "commit", "-m", subject], cwd=cwd)
    if existing_subjects is not None:
        existing_subjects.add(subject)
    return True


def _worktree_has_changes(cwd: Path) -> bool:
    return bool(_worktree_status(cwd).strip())


def _worktree_status(cwd: Path) -> str:
    output = subprocess.check_output(
        ["git", "status", "--porcelain"],
        cwd=cwd,
        text=True,
    )
    return output


def _elapsed_seconds(started_at: float) -> float:
    return round(time.monotonic() - started_at, 6)


def _failure_summary(output: str | bytes | None, *, max_length: int = 240) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        text = output.decode("utf-8", errors="replace")
    else:
        text = output
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    summary = lines[0]
    if len(summary) > max_length:
        return summary[: max_length - 3] + "..."
    return summary


def _extract_test_failures(
    output: str | bytes | None,
) -> list[dict[str, object]]:
    if output is None:
        return []
    if isinstance(output, bytes):
        text = output.decode("utf-8", errors="replace")
    else:
        text = output
    if not text.strip():
        return []
    failures = _extract_pytest_failures(text)
    failures.extend(_extract_vitest_failures(text))
    deduped: list[dict[str, object]] = []
    seen: set[tuple[str, str, str, int | None, str]] = set()
    for failure in failures:
        key = (
            str(failure["runner"]),
            str(failure["name"]),
            str(failure["file"]),
            int(failure["line"]) if isinstance(failure.get("line"), int) else None,
            str(failure["summary"]),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(failure)
        if len(deduped) >= _TEST_FAILURE_MAX_ITEMS:
            break
    return deduped


def _extract_pytest_failures(text: str) -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []
    for match in re.finditer(
        r"(?m)^FAILED\s+(?P<nodeid>\S+?)(?:\s+-\s+(?P<summary>.+))?$",
        text,
    ):
        nodeid = match.group("nodeid").strip()
        if not nodeid:
            continue
        file_path = nodeid.split("::", 1)[0]
        summary = (match.group("summary") or "").strip() or "pytest failure"
        failures.append(
            {
                "runner": "pytest",
                "name": nodeid,
                "file": file_path,
                "line": _extract_source_line(text, file_path),
                "summary": _truncate_text(
                    summary,
                    max_length=_EVENT_METADATA_MAX_STRING_LENGTH,
                ),
            }
        )
    return failures


def _extract_vitest_failures(text: str) -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("FAIL "):
            continue
        header = stripped[len("FAIL ") :].strip()
        if not header:
            continue
        file_path, name = _split_vitest_header(header)
        failures.append(
            {
                "runner": "vitest",
                "name": name,
                "file": file_path,
                "line": _extract_vitest_location(lines, index + 1, file_path),
                "summary": _truncate_text(
                    _extract_vitest_summary(lines, index + 1) or "vitest failure",
                    max_length=_EVENT_METADATA_MAX_STRING_LENGTH,
                ),
            }
        )
    return failures


def _split_vitest_header(header: str) -> tuple[str, str]:
    if " > " not in header:
        return header, header
    file_path, _, name = header.partition(" > ")
    return file_path.strip(), name.strip() or file_path.strip()


def _extract_vitest_location(
    lines: Sequence[str],
    start_index: int,
    file_path: str,
) -> int | None:
    location_re = re.compile(r"^\s*[❯>]\s+(?P<file>[^:]+):(?P<line>\d+):\d+")
    fallback_re = re.compile(r"^\s*at\s+(?P<file>[^:]+):(?P<line>\d+):\d+")
    for line in lines[start_index : start_index + 8]:
        match = location_re.match(line) or fallback_re.match(line)
        if match is None:
            continue
        matched_file = match.group("file").strip()
        if matched_file == file_path:
            return int(match.group("line"))
    return None


def _extract_vitest_summary(lines: Sequence[str], start_index: int) -> str:
    for line in lines[start_index : start_index + 8]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("❯ ", "> ", "at ")):
            continue
        if stripped.startswith(("FAIL ", "stdout", "stderr")):
            continue
        return stripped
    return ""


def _extract_source_line(text: str, file_path: str) -> int | None:
    match = re.search(rf"(?m)^{re.escape(file_path)}:(?P<line>\d+):", text)
    if match is None:
        return None
    return int(match.group("line"))


_BROWSER_OBSERVATION_ALLOWED_KEYS = frozenset(
    {
        "console_error_count",
        "page_error_count",
        "storage_key_count",
        "state_hash",
        "accessibility_summary",
        "source",
        "source_path",
        "reason",
        "parse_error",
    }
)
_BROWSER_OBSERVATION_FORBIDDEN_KEYS = frozenset(
    {
        "raw_screenshot",
        "screenshot",
        "screenshot_path",
        "screenshot_file",
        "playwright_trace",
        "trace",
        "trace_path",
        "trace_file",
        "dom_dump",
        "dom_dump_path",
        "dom_snapshot",
        "dom_snapshot_path",
    }
)
_EVENT_METADATA_MAX_DEPTH = 4
_EVENT_METADATA_MAX_KEYS = 16
_EVENT_METADATA_MAX_ITEMS = 16
_EVENT_METADATA_MAX_STRING_LENGTH = 240
_TEST_FAILURE_MAX_ITEMS = 8
_DEVELOPER_INSTRUCTION_SUMMARY_MAX_LENGTH = 160
_DEVELOPER_INSTRUCTION_MAX_SOURCE_BYTES = 64 * 1024
_DEVELOPER_INSTRUCTION_PRIVATE_PATH_PARTS = frozenset(
    {
        ".git",
        ".ssh",
        ".aws",
        ".config",
    }
)
_DEVELOPER_INSTRUCTION_PRIVATE_PATH_PATTERNS = (
    ".env",
    ".env.local",
    ".env.production",
    "auth.json",
    ".sympohy/config.yaml",
)
_DEVELOPER_INSTRUCTION_ALLOWED_SUFFIXES = frozenset({".md", ".rules"})


def _sanitize_browser_observation_metadata(
    metadata: Mapping[str, object] | None,
) -> dict[str, object]:
    sanitized: dict[str, object] = {}
    if metadata is None:
        return sanitized
    for key in _BROWSER_OBSERVATION_ALLOWED_KEYS:
        if key in metadata:
            sanitized[key] = metadata[key]
    forbidden = sorted(
        key for key in metadata.keys() if key in _BROWSER_OBSERVATION_FORBIDDEN_KEYS
    )
    if forbidden:
        sanitized["redacted_artifacts"] = forbidden
    return sanitized


def _record_browser_observation_boundary(
    *,
    state: _RunStateWriter,
    log_dir: Path,
) -> None:
    source_path = log_dir / "browser-observation.json"
    if not source_path.exists():
        state.record_browser_observation(
            status="skipped",
            summary="browser observation source not configured",
            metadata={
                "source": "browser-observation.json",
                "reason": "missing_lightweight_observation_file",
            },
        )
        return
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        state.record_browser_observation(
            status="failed",
            summary="browser observation source could not be parsed",
            metadata={
                "source": "browser-observation.json",
                "source_path": str(source_path),
                "parse_error": str(exc),
            },
        )
        return
    if not isinstance(payload, Mapping):
        state.record_browser_observation(
            status="failed",
            summary="browser observation source was not an object",
            metadata={
                "source": "browser-observation.json",
                "source_path": str(source_path),
                "parse_error": "expected JSON object",
            },
        )
        return
    state.record_browser_observation(
        status="observed",
        summary="browser observation captured",
        metadata={
            "source": "browser-observation.json",
            "source_path": str(source_path),
            **dict(payload),
        },
    )


def capture_browser_observation(
    *,
    log_dir: Path,
    source_path: Path | None = None,
    metrics: Mapping[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {}
    if source_path is not None:
        source_payload = json.loads(source_path.read_text(encoding="utf-8"))
        if not isinstance(source_payload, Mapping):
            raise ValueError("browser observation source must be a JSON object")
        payload.update(source_payload)
    payload.update(dict(metrics or {}))

    observed = {
        key: payload[key]
        for key in sorted(_BROWSER_OBSERVATION_ALLOWED_KEYS)
        if key in payload and payload[key] is not None
    }
    if not any(
        key in observed
        for key in (
            "console_error_count",
            "page_error_count",
            "storage_key_count",
            "state_hash",
            "accessibility_summary",
        )
    ):
        raise ValueError("browser observation requires at least one lightweight metric")
    observed["source"] = "observe-browser"
    if source_path is not None:
        observed["source_path"] = str(source_path)

    log_dir.mkdir(parents=True, exist_ok=True)
    output_path = log_dir / "browser-observation.json"
    tmp_path = output_path.with_suffix(".json.tmp")
    tmp_path.write_text(
        json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(output_path)
    return {"path": str(output_path), "observation": observed}


def _sanitize_event_metadata(
    *,
    event_type: str,
    metadata: Mapping[str, object] | None,
) -> dict[str, object]:
    if metadata is None:
        return {}
    if event_type == "browser_observation":
        base = _sanitize_browser_observation_metadata(metadata)
    else:
        base = dict(metadata)
    sanitized = _sanitize_metadata_value(base, depth=0)
    if isinstance(sanitized, dict):
        return sanitized
    return {"value": sanitized}


def _sanitize_metadata_value(value: object, *, depth: int) -> object:
    if depth >= _EVENT_METADATA_MAX_DEPTH:
        return "<redacted:depth-limit>"
    if isinstance(value, str):
        return _truncate_text(value, max_length=_EVENT_METADATA_MAX_STRING_LENGTH)
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int | float):
        return value
    if isinstance(value, Mapping):
        sanitized: dict[str, object] = {}
        items = list(value.items())
        for key, item in items[:_EVENT_METADATA_MAX_KEYS]:
            sanitized[str(key)] = _sanitize_metadata_value(item, depth=depth + 1)
        if len(items) > _EVENT_METADATA_MAX_KEYS:
            sanitized["redacted_keys"] = len(items) - _EVENT_METADATA_MAX_KEYS
        return sanitized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sanitized_items = [
            _sanitize_metadata_value(item, depth=depth + 1)
            for item in value[:_EVENT_METADATA_MAX_ITEMS]
        ]
        if len(value) > _EVENT_METADATA_MAX_ITEMS:
            sanitized_items.append(
                f"<redacted:{len(value) - _EVENT_METADATA_MAX_ITEMS} more items>"
            )
        return sanitized_items
    if isinstance(value, (bytes, bytearray)):
        return f"<redacted:{type(value).__name__}:{len(value)} bytes>"
    return _truncate_text(repr(value), max_length=_EVENT_METADATA_MAX_STRING_LENGTH)


def _truncate_text(text: str, *, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return text[:max_length]
    return text[: max_length - 3] + "..."


def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _record_codex_event(
    *,
    state: _RunStateWriter | None,
    role: str,
    model: str | None,
    reasoning_effort: str | None,
    prompt: str,
    parse_status: str,
    duration: float,
    returncode: int,
    failure_summary: str,
) -> None:
    if state is None:
        return
    metadata = {
        "role": role,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "prompt_hash": _prompt_hash(prompt),
        "parse_status": parse_status,
        "returncode": returncode,
        "failure_summary": failure_summary,
    }
    state.record_event(
        event_type="codex",
        status="success" if returncode == 0 and not failure_summary else "failed",
        summary=f"codex {role} {'completed' if returncode == 0 else 'failed'}",
        duration=duration,
        metadata=metadata,
    )


_INSTRUCTION_PATH_RE = re.compile(
    r"(?P<path>(?:"
    r"\.agents/[A-Za-z0-9_./-]+/SKILL\.md|"
    r"docs/[A-Za-z0-9_./-]+\.md|"
    r"(?:[A-Za-z0-9_./-]+/)?AGENTS\.md|"
    r"\.codex/rules/[A-Za-z0-9_.-]+\.rules|"
    r"\.sympohy/config\.yaml"
    r"))"
)


def _record_prompt_instruction_sources(
    *,
    state: _RunStateWriter | None,
    cwd: Path,
    prompt: str,
) -> None:
    if state is None:
        return
    seen: set[str] = set()
    for match in _INSTRUCTION_PATH_RE.finditer(prompt):
        path_text = match.group("path")
        if path_text in seen:
            continue
        seen.add(path_text)
        source_kind = _instruction_source_kind(path_text)
        summary = (
            "codex prompt references repository skill instructions"
            if source_kind == "skill"
            else "codex prompt references repository developer instructions"
        )
        _record_developer_instruction_source(
            state=state,
            cwd=cwd,
            source_kind=source_kind,
            ref=path_text,
            summary=summary,
        )


def _record_developer_instruction_source(
    *,
    state: _RunStateWriter,
    cwd: Path,
    source_kind: str,
    ref: str,
    summary: str,
) -> None:
    metadata = _developer_instruction_metadata(
        cwd=cwd,
        source_kind=source_kind,
        ref=ref,
        summary=summary,
    )
    state.record_event(
        event_type="developer_instruction",
        status="observed",
        summary=f"developer instruction source observed: {metadata['ref']}",
        metadata=metadata,
    )


def _instruction_source_kind(ref: str) -> str:
    if ref.endswith("/SKILL.md"):
        return "skill"
    if ref.endswith(".rules"):
        return "rule"
    if ref.endswith("AGENTS.md"):
        return "agent_instruction"
    if ref == ".sympohy/config.yaml":
        return "config"
    return "doc"


def _developer_instruction_metadata(
    *,
    cwd: Path,
    source_kind: str,
    ref: str,
    summary: str,
) -> dict[str, object]:
    path = cwd / ref
    source_ref = ref
    redaction_reason = _developer_instruction_redaction_reason(path, ref=ref)
    if redaction_reason is None:
        sha256 = _source_sha256(path)
    else:
        sha256 = hashlib.sha256(ref.encode("utf-8")).hexdigest()
        source_ref = f"<redacted:{redaction_reason}>"
    metadata: dict[str, object] = {
        "source_kind": source_kind,
        "path": source_ref,
        "ref": source_ref,
        "sha256": sha256,
        "summary": _truncate_text(
            summary,
            max_length=_DEVELOPER_INSTRUCTION_SUMMARY_MAX_LENGTH,
        ),
    }
    if redaction_reason is not None:
        metadata["redaction"] = redaction_reason
    return metadata


def _developer_instruction_redaction_reason(path: Path, *, ref: str) -> str | None:
    normalized_ref = ref.strip()
    if normalized_ref in _DEVELOPER_INSTRUCTION_PRIVATE_PATH_PATTERNS:
        return "private_config"
    if any(part in _DEVELOPER_INSTRUCTION_PRIVATE_PATH_PARTS for part in path.parts):
        return "private_path"
    if path.suffix and path.suffix not in _DEVELOPER_INSTRUCTION_ALLOWED_SUFFIXES:
        return "unsupported_artifact_type"
    try:
        if path.exists() and path.stat().st_size > _DEVELOPER_INSTRUCTION_MAX_SOURCE_BYTES:
            return "artifact_too_large"
    except OSError:
        return "source_unavailable"
    return None


def _source_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return hashlib.sha256(str(path).encode("utf-8")).hexdigest()


def _merge_has_unmerged_paths(cwd: Path) -> bool:
    output = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=cwd,
        text=True,
    )
    return bool(output.strip())


def _worktree_has_conflict_markers(cwd: Path) -> bool:
    for path in _worktree_changed_paths(cwd):
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if (
            "<<<<<<< " in content
            or "\n=======\n" in content
            or ">>>>>>> " in content
        ):
            return True
    return False


def _worktree_changed_paths(cwd: Path) -> list[Path]:
    paths: list[Path] = []
    for line in _worktree_status(cwd).splitlines():
        if len(line) < 4:
            continue
        path_text = line[3:]
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1]
        path = cwd / path_text
        if path.exists() and path.is_file():
            paths.append(path)
    return paths


def _summarize_status(status: str, *, limit: int = 5) -> str:
    lines = [line.strip() for line in status.splitlines() if line.strip()]
    if not lines:
        return "no changes reported"
    summary = "; ".join(lines[:limit])
    if len(lines) > limit:
        summary += f"; and {len(lines) - limit} more"
    return summary


def _summarize_review_findings(
    findings: Sequence[ReviewFinding],
    *,
    limit: int = 3,
) -> str:
    lines = [f"{finding.severity}: {finding.summary}" for finding in findings]
    if not lines:
        return "none"
    summary = "; ".join(lines[:limit])
    if len(lines) > limit:
        summary += f"; and {len(lines) - limit} more"
    return summary


def _unsafe_resume_reason(
    category: str,
    reason: str | None,
    state_path: Path | None,
) -> str:
    parts = [category]
    if reason:
        parts.append(reason)
    if state_path is not None:
        parts.append(f"state path: {state_path}")
    return "; ".join(parts)


def _last_progress(state: Mapping[str, object] | None) -> Mapping[str, object]:
    if state is None:
        return {}
    progress = state.get("last_known_progress")
    if isinstance(progress, Mapping):
        return progress
    return {}


def _progress_int(state: Mapping[str, object] | None, key: str) -> int | None:
    value = _last_progress(state).get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _review_start_round(state: Mapping[str, object] | None) -> int:
    round_index = _progress_int(state, "review_round")
    if round_index is None:
        return 1
    message = _last_progress(state).get("message")
    if message in {"pushed review fix", "review fix commit already exists"}:
        return round_index + 1
    return round_index


def _next_review_rerun_round(log_dir: Path, *, max_review_rounds: int) -> int:
    review_rounds: list[int] = []
    for path in log_dir.glob("review-*.json"):
        try:
            review_rounds.append(int(path.stem.removeprefix("review-")))
        except ValueError:
            continue
    if not review_rounds:
        return 1
    return min(max(review_rounds) + 1, max_review_rounds + 1)


def _bootstrap_run_state(
    issue: Issue,
    config: SympohyConfig,
    log_dir: Path,
    *,
    phase: str,
    reason: str | None,
    run_id: str | None = None,
    lock_path: Path | None = None,
) -> Mapping[str, object]:
    worktree = config.worktree_root / f"issue-{issue.number}"
    branch = f"issue-{issue.number}-sympohy"
    if worktree.exists():
        try:
            branch = _current_branch(worktree)
        except subprocess.CalledProcessError:
            pass
    plan_path = log_dir / "plan.json"
    progress: dict[str, object] = {
        "message": "routing stale running issue into resume handling",
        "stale_reason": reason,
        "worktree_exists": worktree.exists(),
        "plan_exists": plan_path.exists(),
    }
    if worktree.exists() and plan_path.exists():
        plan = _load_existing_plan(plan_path)
        if plan is not None:
            logical_steps = _logical_steps(plan)
            recovery = _infer_implementation_recovery(
                issue.number,
                cwd=worktree,
                base_branch=config.base_branch,
                total_steps=len(logical_steps),
            )
            progress.update(
                {
                    "completed_logical_steps": recovery.committed_logical_steps,
                    "total_logical_steps": len(logical_steps),
                    "worktree_clean": recovery.worktree_clean,
                    "unsafe_resume_reason": recovery.unsafe_reason,
                    "resume_action": recovery.resume_action(len(logical_steps)),
                }
            )
    if worktree.exists():
        try:
            progress["pull_request_exists"] = _pull_request_exists(
                branch=branch,
                cwd=worktree,
            )
        except (OSError, subprocess.SubprocessError, _AmbiguousPullRequestError):
            progress["pull_request_exists"] = None
    writer = _RunStateWriter(
        issue_number=issue.number,
        log_dir=log_dir,
        base_branch=config.base_branch,
        worktree=worktree if worktree.exists() else None,
        branch=branch,
        plan_path=plan_path if plan_path.exists() else None,
        run_id=run_id,
        lock_path=lock_path,
        refresh_lock=lock_path is not None,
    )
    writer.write(
        phase=phase,
        progress=progress,
    )
    writer.record_recovery(
        "stale_run_bootstrapped",
        {
            "stale_reason": reason,
            "phase": phase,
            "worktree_exists": worktree.exists(),
            "plan_exists": plan_path.exists(),
        },
    )
    state = read_run_state(writer.state_path)
    return state or {}


def _existing_run_refusal_reason(
    issue: Issue,
    config: SympohyConfig,
    log_dir: Path,
) -> str | None:
    state_path = log_dir / "state.json"
    if state_path.exists():
        return f"existing run state found at {state_path}; use resume"
    worktree = config.worktree_root / f"issue-{issue.number}"
    if worktree.exists():
        return f"existing worktree found at {worktree}; use resume"
    branch = f"issue-{issue.number}-sympohy"
    if _branch_exists(branch):
        return f"existing branch found at {branch}; use resume"
    if _remote_branch_exists(branch):
        return f"existing remote branch found at origin/{branch}; use resume"
    return None


def _resolve_resume_point_for_issue(
    labels: object,
    state: Mapping[str, object] | None,
    *,
    issue_state: str | None = None,
    issue_state_reason: str | None = None,
):
    names = set(_label_names(labels))
    closed_as_completed = issue_state in {"CLOSED", "closed"} and issue_state_reason in {
        "COMPLETED",
        "completed",
    }
    if closed_as_completed or "sympohy:done" in names:
        return resolve_resume_point(
            labels,
            state={
                **(dict(state) if state is not None else {}),
                "status": "done",
                "phase": "finalize",
            },
        )
    if state is not None and state.get("status") == "blocked":
        phase = phase_from_state(state) or _phase_from_labels(names)
        if (
            "sympohy:blocked" in names
            and phase in {"review", "fix", "finalize"}
        ) or (
            "sympohy:blocked" not in names
            and ("sympohy:running" in names or "sympohy:pending" in names)
        ):
            state = {**state, "status": "running"}
    return resolve_resume_point(labels, state=state)


def _should_resume_missing_plan_as_planning(
    *,
    resume_point: str,
    state: Mapping[str, object] | None,
    plan_path: Path,
) -> bool:
    if resume_point != "implement":
        return False
    if _load_existing_plan(plan_path) is not None:
        return False
    message = _last_progress(state).get("message")
    if message not in {
        "starting implementation planning",
        "pushing initial issue branch and opening draft pull request",
        "preparing feature documentation artifacts",
        "running stage gate",
        "repairing feature documentation artifact evidence",
    }:
        return False
    return (
        _progress_int(state, "current_logical_step") is None
        and _progress_int(state, "completed_logical_steps") is None
        and _progress_int(state, "total_logical_steps") is None
    )


def _issue_branch_exists(issue: Issue) -> bool:
    branch = f"issue-{issue.number}-sympohy"
    return _branch_exists(branch) or _remote_branch_exists(branch)


def _ensure_draft_pull_request(
    *,
    cwd: Path,
    issue_number: int | None = None,
    heartbeat: Callable[[], None] | None = None,
    state: _RunStateWriter | None = None,
) -> None:
    branch = _current_branch(cwd)
    if _pull_request_exists(branch=branch, cwd=cwd):
        _ensure_existing_pull_request_metadata(
            cwd=cwd,
            issue_number=issue_number or _issue_number_from_branch(branch),
            heartbeat=heartbeat,
            state=state,
        )
        return
    if issue_number is None:
        raise ValueError("issue_number is required when creating a draft pull request")
    body = _render_pull_request_body(issue_number=issue_number, cwd=cwd)
    body_file_path: Path | None = None
    try:
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=cwd,
            prefix="sympohy-pr-body-",
            suffix=".md",
            delete=False,
        ) as handle:
            handle.write(body)
            body_file_path = Path(handle.name)
        _check_call_with_heartbeat(
            [
                "gh",
                "pr",
                "create",
                "--draft",
                "--fill",
                "--body-file",
                str(body_file_path),
            ],
            cwd=cwd,
            heartbeat=heartbeat,
            state=state,
        )
    finally:
        if body_file_path is not None:
            body_file_path.unlink(missing_ok=True)


def _push_branch_and_ensure_draft_pull_request(
    *,
    cwd: Path,
    branch: str,
    heartbeat: Callable[[], None] | None = None,
    issue_number: int | None = None,
    base_branch: str | None = None,
    state: _RunStateWriter | None = None,
) -> None:
    if issue_number is not None and base_branch is not None:
        _ensure_initial_pull_request_commit(
            issue_number=issue_number,
            cwd=cwd,
            base_branch=base_branch,
        )
    _check_call_with_heartbeat(
        ["git", "push", "-u", "origin", branch],
        cwd=cwd,
        heartbeat=heartbeat,
        state=state,
    )
    _ensure_draft_pull_request(
        cwd=cwd,
        issue_number=issue_number,
        heartbeat=heartbeat,
        state=state,
    )


def _ensure_initial_pull_request_commit(
    *,
    issue_number: int,
    cwd: Path,
    base_branch: str,
) -> None:
    if _branch_has_commits(cwd=cwd, base_branch=base_branch):
        return
    subject = f"#{issue_number} chore(sympohy): open draft pull request"
    if not validate_commit_subject(subject):
        raise ValueError(f"invalid generated commit subject: {subject}")
    subprocess.check_call(["git", "commit", "--allow-empty", "-m", subject], cwd=cwd)


def _render_pull_request_body(*, issue_number: int, cwd: Path) -> str:
    template_path = cwd / ".github" / "pull_request_template.md"
    if not template_path.exists():
        template_path = Path(__file__).resolve().parents[2] / ".github" / "pull_request_template.md"
    template_body = template_path.read_text(encoding="utf-8").rstrip()
    return (
        "## Issue Traceability\n"
        f"- Closes #{issue_number}\n\n"
        f"{template_body}\n"
    )


def _ensure_existing_pull_request_metadata(
    *,
    cwd: Path,
    issue_number: int | None,
    heartbeat: Callable[[], None] | None = None,
    state: _RunStateWriter | None = None,
) -> None:
    payload = json.loads(
        subprocess.check_output(
            ["gh", "pr", "view", "--json", "number,body"],
            cwd=cwd,
            text=True,
        )
    )
    if not isinstance(payload, Mapping):
        raise _PullRequestMetadataError(
            "could not inspect existing pull request metadata"
        )
    pull_request_number = payload.get("number")
    body = payload.get("body")
    if not isinstance(body, str):
        raise _PullRequestMetadataError(
            "existing pull request metadata returned a non-string body"
        )
    if issue_number is None:
        raise _PullRequestMetadataError(
            "existing pull request "
            f"#{pull_request_number if pull_request_number is not None else 'unknown'} "
            "issue number could not be derived for metadata backfill"
        )
    updated_body = _supplement_pull_request_metadata(
        body,
        issue_number=issue_number,
        cwd=cwd,
    )
    if updated_body == body:
        return
    _update_pull_request_body(
        cwd=cwd,
        pull_request_number=pull_request_number,
        body=updated_body,
        heartbeat=heartbeat,
        state=state,
    )


def _missing_pull_request_metadata_sections(body: str) -> list[str]:
    required_sections = (
        ("Issue Traceability", "## Issue Traceability"),
        ("Summary", "## 概要"),
        ("Validation", "## 動作確認結果"),
    )
    return [label for label, marker in required_sections if marker not in body]


def _issue_number_from_branch(branch: str) -> int | None:
    match = re.match(r"^issue-(?P<issue>\d+)-", branch.strip())
    if match is None:
        return None
    return int(match.group("issue"))


def _supplement_pull_request_metadata(
    body: str,
    *,
    issue_number: int,
    cwd: Path,
) -> str:
    canonical_body = _render_pull_request_body(issue_number=issue_number, cwd=cwd)
    if not body.strip():
        return canonical_body

    updated = body.rstrip() + "\n"
    missing_sections = _missing_pull_request_metadata_sections(updated)
    if not missing_sections:
        return body
    for label in missing_sections:
        marker = _pull_request_metadata_marker(label)
        section = _extract_markdown_section(canonical_body, marker)
        if section is None:
            raise _PullRequestMetadataError(
                f"pull request template missing required section: {label}"
            )
        if marker == "## Issue Traceability":
            updated = section.rstrip() + "\n\n" + updated.lstrip()
        else:
            updated = updated.rstrip() + "\n\n" + section.rstrip() + "\n"
    return updated


def _pull_request_metadata_marker(label: str) -> str:
    markers = {
        "Issue Traceability": "## Issue Traceability",
        "Summary": "## 概要",
        "Validation": "## 動作確認結果",
    }
    return markers[label]


def _extract_markdown_section(body: str, marker: str) -> str | None:
    start = body.find(marker)
    if start == -1:
        return None
    next_heading = body.find("\n## ", start + len(marker))
    if next_heading == -1:
        return body[start:].rstrip() + "\n"
    return body[start:next_heading].rstrip() + "\n"


def _update_pull_request_body(
    *,
    cwd: Path,
    pull_request_number: object,
    body: str,
    heartbeat: Callable[[], None] | None = None,
    state: _RunStateWriter | None = None,
) -> None:
    body_file_path: Path | None = None
    try:
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=cwd,
            prefix="sympohy-pr-body-",
            suffix=".md",
            delete=False,
        ) as handle:
            handle.write(body)
            body_file_path = Path(handle.name)
        command = ["gh", "pr", "edit"]
        if pull_request_number is not None:
            command.append(str(pull_request_number))
        command.extend(["--body-file", str(body_file_path)])
        _check_call_with_heartbeat(
            command,
            cwd=cwd,
            heartbeat=heartbeat,
            state=state,
        )
    finally:
        if body_file_path is not None:
            body_file_path.unlink(missing_ok=True)


def _branch_has_commits(*, cwd: Path, base_branch: str) -> bool:
    try:
        output = subprocess.check_output(
            ["git", "rev-list", "--count", f"{base_branch}..HEAD"],
            cwd=cwd,
            text=True,
        )
    except subprocess.CalledProcessError:
        return True
    try:
        return int(output.strip() or "0") > 0
    except ValueError:
        return True


def _pull_request_merged(*, cwd: Path) -> bool:
    result = subprocess.run(
        ["gh", "pr", "view", "--json", "state,mergedAt"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, Mapping):
        return False
    merged_at = payload.get("mergedAt")
    return isinstance(merged_at, str) and bool(merged_at)


def _pull_request_exists(*, branch: str, cwd: Path) -> bool:
    result = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "open",
            "--json",
            "number",
        ],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        try:
            payload = json.loads(result.stdout or "[]")
        except json.JSONDecodeError:
            payload = []
        if isinstance(payload, list):
            if len(payload) > 1:
                numbers = [
                    str(item.get("number"))
                    for item in payload
                    if isinstance(item, Mapping) and item.get("number") is not None
                ]
                raise _AmbiguousPullRequestError(
                    f"multiple open pull requests found for head branch {branch}: "
                    f"{', '.join(numbers) or 'unknown PR numbers'}"
                )
            if len(payload) == 1:
                return True

    if result.returncode == 0:
        return False

    result = subprocess.run(
        ["gh", "pr", "view", "--json", "headRefName,state"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, Mapping):
        return False
    return payload.get("headRefName") == branch and payload.get("state") == "OPEN"


def _branch_exists(branch: str) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _remote_branch_exists(branch: str) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{branch}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _worktree_for_branch(branch: str) -> Path | None:
    try:
        output = subprocess.check_output(
            ["git", "worktree", "list", "--porcelain"],
            text=True,
        )
    except subprocess.CalledProcessError:
        return None

    current_path: Path | None = None
    for line in output.splitlines():
        if line.startswith("worktree "):
            current_path = Path(line.removeprefix("worktree "))
        elif line == f"branch refs/heads/{branch}" and current_path is not None:
            return current_path
        elif line == "":
            current_path = None
    return None


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


def _phase_from_labels(labels: Iterable[str]) -> str | None:
    phases = [
        label.removeprefix("sympohy:phase:")
        for label in labels
        if label.startswith("sympohy:phase:")
    ]
    return phases[0] if len(phases) == 1 else None
