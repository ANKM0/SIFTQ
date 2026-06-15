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
from typing import Callable, Iterable, Mapping, Sequence

from .config import SympohyConfig
from .core import (
    extract_acceptance_set,
    inspect_running_issue,
    merge_gate_allows_merge,
    next_retry_action,
    parse_review_json,
    resolve_resume_point,
    validate_commit_subject,
)
from .github import Issue, comment, fetch_issue, list_candidate_issues, set_issue_state


HEARTBEAT_INTERVAL_SECONDS = 30
LOGICAL_STEP_COMMIT_RE = re.compile(
    r"^#(?P<issue>\d+) feat\(sympohy\): implement logical step (?P<step>\d+)$"
)


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
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.issue_number = issue_number
        self.log_dir = log_dir
        self.base_branch = base_branch
        self.worktree = worktree
        self.branch = branch
        self.plan_path = plan_path
        self.phase: str | None = None
        self.status = "running"
        self.last_known_progress: Mapping[str, object] = {}
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
        payload = {
            "issue": self.issue_number,
            "phase": self.phase,
            "status": self.status,
            "pid": os.getpid(),
            "heartbeat": _isoformat_utc(self._clock()),
            "branch": self.branch,
            "worktree": {
                "path": str(self.worktree) if self.worktree is not None else None,
                "branch": self.branch,
                "base_branch": self.base_branch,
            },
            "plan_reference": str(self.plan_path) if self.plan_path is not None else None,
            "last_known_progress": dict(self.last_known_progress),
        }
        tmp_path = self.state_path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(self.state_path)

    def heartbeat(self) -> None:
        self.write()


def ensure_worktree(issue: Issue, config: SympohyConfig) -> Path:
    worktree = config.worktree_root / f"issue-{issue.number}"
    branch = f"issue-{issue.number}-sympohy"
    if worktree.exists():
        return worktree

    worktree.parent.mkdir(parents=True, exist_ok=True)
    if _branch_exists(branch):
        subprocess.check_call(["git", "worktree", "add", str(worktree), branch])
    else:
        subprocess.check_call(
            ["git", "worktree", "add", "-b", branch, str(worktree), config.base_branch]
        )
    return worktree


def watch(config: SympohyConfig) -> int:
    candidates = list_candidate_issues(limit=100, run_log_root=config.run_log_root)
    selected = candidates[: config.max_workers]
    processes: list[subprocess.Popen[bytes]] = []

    for issue in selected:
        number = int(issue["number"])
        labels = _label_names(issue.get("labels", []))
        if "sympohy:running" in labels:
            inspection = inspect_running_issue(issue, run_log_root=config.run_log_root)
            if not inspection.stale:
                continue
            processes.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "scripts.sympohy",
                        "resume",
                        f"#{number}",
                    ]
                )
            )
            continue

        set_issue_state(
            f"#{number}",
            current_labels=labels,
            status="sympohy:pending",
            phase="triage",
        )
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "scripts.sympohy",
                    "run",
                    f"#{number}",
                ]
            )
        )

    return 0 if all(process.poll() in {None, 0} for process in processes) else 1


def resume_issue(issue_ref: str, config: SympohyConfig) -> int:
    issue = fetch_issue(issue_ref)
    labels = [{"name": label} for label in issue.labels]
    resume_point = resolve_resume_point(labels)
    log_dir = config.run_log_root / f"issue-{issue.number}"

    if resume_point.terminal:
        state = _RunStateWriter(
            issue_number=issue.number,
            log_dir=log_dir,
            base_branch=config.base_branch,
        )
        state.write(
            phase=resume_point.phase or "triage",
            status="done" if resume_point.name == "completed" else resume_point.name,
            progress={
                "message": "resume skipped for terminal issue state",
                "resume_point": resume_point.name,
            },
        )
        return 0

    payload = {
        "number": issue.number,
        "state": "OPEN",
        "labels": labels,
    }
    inspection = inspect_running_issue(payload, run_log_root=config.run_log_root)
    if not inspection.stale:
        return 0

    state = _RunStateWriter(
        issue_number=issue.number,
        log_dir=log_dir,
        base_branch=config.base_branch,
    )
    state.write(
        phase=inspection.phase or "triage",
        progress={
            "message": "routing stale running issue into resume handling",
            "resume_point": resume_point.name,
            "stale_reason": inspection.reason,
            "stale_state_path": str(inspection.state_path)
            if inspection.state_path is not None
            else None,
        },
    )

    if inspection.reason in {
        "missing phase label",
        "missing state",
        "missing pid",
        "missing heartbeat",
    }:
        _block(
            issue_ref,
            phase=inspection.phase or resume_point.phase or "triage",
            failed_command="resume safety check",
            attempts=1,
            cause=_unsafe_resume_reason(
                "missing required run state",
                inspection.reason,
                inspection.state_path,
            ),
            run_log_path=log_dir,
            cwd=None,
            state=state,
            current_labels=issue.labels,
        )
        return 2

    return run_issue(issue_ref, config, recover=resume_point.name != "planning")


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


def run_issue(issue_ref: str, config: SympohyConfig, *, recover: bool = False) -> int:
    issue = fetch_issue(issue_ref)
    log_dir = config.run_log_root / f"issue-{issue.number}"
    state = _RunStateWriter(
        issue_number=issue.number,
        log_dir=log_dir,
        base_branch=config.base_branch,
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

    worktree = ensure_worktree(issue, config)
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
        )
    logical_steps = _logical_steps(plan)
    total_steps = len(logical_steps)
    recovery = (
        _infer_implementation_recovery(
            issue.number,
            cwd=worktree,
            base_branch=config.base_branch,
            total_steps=total_steps,
        )
        if recover
        else _ImplementationRecovery(committed_logical_steps=0)
    )
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
                config.retry_max_attempts,
                worktree,
                log_dir,
                state=state,
                logical_step=index,
                total_logical_steps=total_steps,
            ) != 0:
                _block(
                    issue_ref,
                    phase="hooks",
                    failed_command="; ".join(config.hooks),
                    attempts=config.retry_max_attempts,
                    cause="verification hooks still failed after retries",
                    run_log_path=log_dir,
                    cwd=worktree,
                    state=state,
                )
                return 2
            committed = _commit_all_if_new(
                subject,
                cwd=worktree,
                base_branch=config.base_branch,
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
        phase="review",
        branch=branch,
        progress={
            "message": "pushing branch and opening draft pull request",
            "completed_logical_steps": total_steps,
            "total_logical_steps": total_steps,
        },
    )
    subprocess.check_call(["git", "push", "-u", "origin", branch], cwd=worktree)
    _ensure_draft_pull_request(cwd=worktree)
    review_result = _review_fix_loop(issue_ref, issue, config, worktree, log_dir, state)
    if review_result != 0:
        return review_result

    final_verifier_path = log_dir / "final-verifier.json"
    state.write(
        phase="merge",
        progress={
            "message": "running final verifier",
            "completed_logical_steps": total_steps,
            "total_logical_steps": total_steps,
            "log_path": str(final_verifier_path),
        },
    )
    final = _codex_json(
        [
            "Act as final verifier. Return JSON with boolean "
            "acceptance_criteria_satisfied, boolean definition_of_done_satisfied, "
            "and merge_recommendation set to merge or block.",
            f"Issue #{issue.number}",
        ],
        cwd=worktree,
        log_path=final_verifier_path,
        heartbeat=state.heartbeat,
    )
    empty_review = parse_review_json('{"findings":[]}')
    if not merge_gate_allows_merge(
        final_verifier=final,
        github_checks_status="success",
        review_result=empty_review,
    ):
        _block(
            issue_ref,
            phase="merge",
            failed_command="final verifier",
            attempts=1,
            cause="final verifier did not recommend merge",
            run_log_path=log_dir,
            cwd=worktree,
            state=state,
        )
        return 2

    state.write(
        phase="merge",
        progress={
            "message": "merging pull request",
            "completed_logical_steps": total_steps,
            "total_logical_steps": total_steps,
        },
    )
    subprocess.check_call(["gh", "pr", "ready"], cwd=worktree)
    subprocess.check_call(["gh", "pr", "checks", "--watch"], cwd=worktree)
    subprocess.check_call(["gh", "pr", "merge", "--squash", "--delete-branch"], cwd=worktree)
    subprocess.check_call(["git", "worktree", "remove", str(worktree)])
    state.write(
        phase="merge",
        status="done",
        progress={
            "message": "merged pull request and removed worktree",
            "completed_logical_steps": total_steps,
            "total_logical_steps": total_steps,
        },
    )
    set_issue_state(
        issue_ref,
        current_labels=("sympohy:running", "sympohy:phase:merge"),
        status="sympohy:done",
        phase="merge",
    )
    subprocess.check_call(["gh", "issue", "close", issue_ref])
    return 0


def _run_hooks(
    hooks: Iterable[str],
    retry_max_attempts: int,
    cwd: Path,
    log_dir: Path,
    *,
    state: _RunStateWriter | None = None,
    logical_step: int | None = None,
    total_logical_steps: int | None = None,
) -> int:
    for command in hooks:
        attempts = 0
        while True:
            attempts += 1
            log_path = log_dir / f"hook-{attempts}.log"
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
                log_path=log_dir / f"hook-fix-{attempts}.log",
                heartbeat=state.heartbeat if state is not None else None,
            )
    return 0


def _review_fix_loop(
    issue_ref: str,
    issue: Issue,
    config: SympohyConfig,
    cwd: Path,
    log_dir: Path,
    state: _RunStateWriter,
) -> int:
    for round_index in range(1, config.review_max_rounds + 1):
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
                "with findings: [{severity, summary, status}]. Severities are "
                "critical, high, medium, low, info.",
                f"Issue #{issue.number}",
            ],
            cwd=cwd,
            log_path=review_log_path,
            heartbeat=state.heartbeat,
        )
        review = parse_review_json(review_json)
        pr_number = subprocess.check_output(
            ["gh", "pr", "view", "--json", "number", "--jq", ".number"],
            cwd=cwd,
            text=True,
        ).strip()
        comment(pr_number, review_json, cwd=cwd)
        if review.approved:
            return 0
        if round_index == config.review_max_rounds:
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
        set_issue_state(
            issue_ref,
            current_labels=("sympohy:running", "sympohy:phase:fix"),
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
        )
        subject = f"#{issue.number} fix(sympohy): resolve review finding {round_index}"
        committed = _commit_all_if_new(
            subject,
            cwd=cwd,
            base_branch=config.base_branch,
        )
        if committed:
            subprocess.check_call(["git", "push"], cwd=cwd)
        state.write(
            phase="review",
            progress={
                "message": "pushed review fix"
                if committed
                else "review fix commit already exists",
                "review_round": round_index,
                "commit_subject": subject,
            },
        )
    return 2


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
) -> Mapping[str, object]:
    output = _codex_text(prompts, cwd=cwd, log_path=log_path, heartbeat=heartbeat)
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
) -> str:
    prompt = "\n\n".join(prompts)
    output = _check_output_with_heartbeat(
        ["codex", "exec", prompt],
        cwd=cwd,
        heartbeat=heartbeat,
    )
    log_path.write_text(output, encoding="utf-8")
    return output


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
                heartbeat()
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
                heartbeat()


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


def _logical_steps(plan: Mapping[str, object]) -> list[object]:
    steps = plan.get("logical_steps", [])
    if not isinstance(steps, list) or not steps:
        raise ValueError("plan JSON must contain non-empty logical_steps")
    logical_steps = [
        step
        for step in steps
        if isinstance(step, Mapping) or (isinstance(step, str) and step.strip())
    ]
    if not logical_steps:
        raise ValueError("plan JSON must contain non-empty logical_steps")
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


def _commit_subject_exists(subject: str, *, cwd: Path, base_branch: str) -> bool:
    return subject in _commit_subjects(cwd=cwd, base_branch=base_branch)


def _commit_all_if_new(subject: str, *, cwd: Path, base_branch: str) -> bool:
    if _commit_subject_exists(subject, cwd=cwd, base_branch=base_branch):
        return False

    subprocess.check_call(["git", "add", "-A"], cwd=cwd)
    if not _worktree_has_changes(cwd):
        if _commit_subject_exists(subject, cwd=cwd, base_branch=base_branch):
            return False
        raise RuntimeError(f"no changes to commit for subject: {subject}")

    subprocess.check_call(["git", "commit", "-m", subject], cwd=cwd)
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


def _ensure_draft_pull_request(*, cwd: Path) -> None:
    branch = _current_branch(cwd)
    if _pull_request_exists(branch=branch, cwd=cwd):
        return
    subprocess.check_call(["gh", "pr", "create", "--draft", "--fill"], cwd=cwd)


def _pull_request_exists(*, branch: str, cwd: Path) -> bool:
    result = subprocess.run(
        ["gh", "pr", "view", "--json", "number"],
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return True

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
            "--jq",
            ".[0].number",
        ],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def _branch_exists(branch: str) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
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
