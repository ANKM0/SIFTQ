from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import uuid
from typing import Callable, Iterable, Mapping, Sequence

from .config import SympohyConfig
from .core import (
    AcceptanceSet,
    FinalVerifierFinding,
    PHASE_ALIASES,
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
        self.write(progress=self.last_known_progress)


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
            issue=issue,
            acceptance=acceptance,
            worktree=worktree,
            log_path=decisions_path,
            heartbeat=state.heartbeat,
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
                issue=issue,
                acceptance=acceptance,
                worktree=worktree,
                log_path=fix_log_path,
                heartbeat=state.heartbeat,
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
    issue: Issue,
    acceptance: AcceptanceSet,
    worktree: Path,
    log_path: Path,
    heartbeat: Callable[[], None] | None,
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
    resume_point = resolve_resume_point(labels, state=state_payload)

    if resume_point.terminal:
        terminal_phase = resume_point.phase or (
            "merge" if resume_point.name == "completed" else "triage"
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
            from_resume=False,
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
        resume_point = resolve_resume_point(labels, state=state_payload)
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
            resume_point = resolve_resume_point(labels, state=state_payload)
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

    return run_issue(
        issue_ref,
        config,
        recover=resume_point.name != "planning",
        from_resume=True,
        resume_point=resume_point.name,
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
        worktree = ensure_worktree(issue, config, recover=recover)
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
                        json.dumps(step, ensure_ascii=False),
                        "Use normal Codex user config and repository rules.",
                    ],
                    cwd=worktree,
                    log_path=implement_log_path,
                    heartbeat=state.heartbeat,
                    config=config,
                    role="implementation",
                )
            state.write(
                phase="hooks",
                progress={
                    "message": "running verification hooks",
                    "current_logical_step": index,
                    "completed_logical_steps": index,
                    "total_logical_steps": total_steps,
                },
            )
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
            "message": "pushing branch and opening draft pull request",
            "completed_logical_steps": total_steps,
            "total_logical_steps": total_steps,
        },
    )
    try:
        _push_branch_and_ensure_draft_pull_request(
            issue=issue,
            cwd=worktree,
            branch=branch,
            heartbeat=state.heartbeat,
        )
    except _AmbiguousPullRequestError as exc:
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
    if _pull_request_merged(cwd=worktree):
        return _finish_merged_issue(
            issue_ref,
            worktree,
            state,
            total_steps=_progress_int(previous_state, "total_logical_steps"),
            message="reconciled already-merged pull request",
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
                issue=issue,
                cwd=worktree,
                branch=branch,
                heartbeat=state.heartbeat,
            )
        except _AmbiguousPullRequestError as exc:
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
        _check_call_with_heartbeat(["git", "push"], cwd=cwd, heartbeat=state.heartbeat)
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
    )
    committed = _commit_all_if_new(
        subject,
        cwd=cwd,
        base_branch=config.base_branch,
        existing_subjects=existing_fix_subjects,
    )
    if committed:
        _check_call_with_heartbeat(["git", "push"], cwd=cwd, heartbeat=state.heartbeat)
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
    )
    _check_call_with_heartbeat(
        ["gh", "pr", "checks", "--watch"],
        cwd=worktree,
        heartbeat=state.heartbeat,
    )
    _check_call_with_heartbeat(
        ["gh", "pr", "merge", "--squash", "--delete-branch"],
        cwd=worktree,
        heartbeat=state.heartbeat,
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
        _check_call_with_heartbeat(["git", "push"], cwd=cwd, heartbeat=state.heartbeat)
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
        subprocess.check_call(["git", "worktree", "remove", str(worktree)])
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
    subprocess.check_call(["gh", "issue", "close", issue_ref])
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
            with log_path.open("w", encoding="utf-8") as log:
                returncode = _run_command_with_heartbeat(
                    shlex.split(command),
                    cwd=cwd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    heartbeat=state.heartbeat if state is not None else None,
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
            )
    return 0


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
) -> int:
    if start_round > config.review_max_rounds + 1:
        return 0
    if pull_request_number is None:
        pull_request_number = _resolve_pull_request_number(cwd)
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
        )
        review = parse_review_json(review_json)
        review_json = _review_json_with_stage_status(review)
        review_log_path.write_text(review_json, encoding="utf-8")
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
) -> None:
    if state is not None:
        state.write(
            phase=phase,
            status="blocked",
            progress={
                "message": "blocked",
                "failed_command": failed_command,
                "attempts": attempts,
                "cause": cause,
                "run_log_path": str(run_log_path),
            },
        )
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
) -> Mapping[str, object]:
    output = _codex_text(
        prompts,
        cwd=cwd,
        log_path=log_path,
        heartbeat=heartbeat,
        config=config,
        role=role,
    )
    payload = json.loads(output)
    if not isinstance(payload, Mapping):
        raise ValueError("Codex JSON output must be an object")
    return payload


def _codex_text(
    prompts: Sequence[str],
    *,
    cwd: Path,
    log_path: Path,
    heartbeat: Callable[[], None] | None = None,
    config: SympohyConfig | None = None,
    role: str = "default",
) -> str:
    prompt = "\n\n".join(prompts)
    output = _check_output_with_heartbeat(
        _codex_exec_args(prompt, config=config, role=role),
        cwd=cwd,
        heartbeat=heartbeat,
    )
    log_path.write_text(output, encoding="utf-8")
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
) -> str:
    process = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, text=True)
    while True:
        try:
            output, _ = process.communicate(timeout=HEARTBEAT_INTERVAL_SECONDS)
        except subprocess.TimeoutExpired:
            if heartbeat is not None:
                try:
                    heartbeat()
                except Exception:
                    _terminate_process(process)
                    raise
            continue
        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode,
                args,
                output=output,
            )
        return output


def _run_command_with_heartbeat(
    args: Sequence[str],
    *,
    cwd: Path,
    heartbeat: Callable[[], None] | None = None,
    **popen_kwargs: object,
) -> int:
    process = subprocess.Popen(args, cwd=cwd, **popen_kwargs)
    while True:
        try:
            return process.wait(timeout=HEARTBEAT_INTERVAL_SECONDS)
        except subprocess.TimeoutExpired:
            if heartbeat is not None:
                try:
                    heartbeat()
                except Exception:
                    _terminate_process(process)
                    raise


def _check_call_with_heartbeat(
    args: Sequence[str],
    *,
    cwd: Path,
    heartbeat: Callable[[], None] | None = None,
) -> None:
    returncode = _run_command_with_heartbeat(args, cwd=cwd, heartbeat=heartbeat)
    if returncode != 0:
        raise subprocess.CalledProcessError(returncode, args)


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


def _summarize_status(status: str, *, limit: int = 5) -> str:
    lines = [line.strip() for line in status.splitlines() if line.strip()]
    if not lines:
        return "no changes reported"
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


def _ensure_draft_pull_request(
    *,
    issue: Issue,
    cwd: Path,
    heartbeat: Callable[[], None] | None = None,
) -> None:
    branch = _current_branch(cwd)
    if _pull_request_exists(branch=branch, cwd=cwd):
        return
    title = _draft_pull_request_title(issue)
    body = _draft_pull_request_body(issue)
    _check_call_with_heartbeat(
        ["gh", "pr", "create", "--draft", "--title", title, "--body", body],
        cwd=cwd,
        heartbeat=heartbeat,
    )


def _push_branch_and_ensure_draft_pull_request(
    *,
    issue: Issue,
    cwd: Path,
    branch: str,
    heartbeat: Callable[[], None] | None = None,
) -> None:
    _check_call_with_heartbeat(
        ["git", "push", "-u", "origin", branch],
        cwd=cwd,
        heartbeat=heartbeat,
    )
    _ensure_draft_pull_request(issue=issue, cwd=cwd, heartbeat=heartbeat)


def _draft_pull_request_title(issue: Issue) -> str:
    return f"#{issue.number} {issue.title.strip()}".strip()


def _draft_pull_request_body(issue: Issue) -> str:
    return "\n".join(
        [
            "## Summary",
            f"- Addresses #{issue.number}",
            f"- {issue.title.strip() or f'Implement #{issue.number}'}",
            "",
            "## Validation",
            "- [ ] uv run python -m pytest tests/sympohy -q",
            "- [ ] task ci:sympohy",
            "- [ ] task ci:markdown",
            "- [ ] task codd:validate",
            "- [ ] GitHub checks are passing",
        ]
    )


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
