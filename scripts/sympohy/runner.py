from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Iterable, Mapping, Sequence

from .config import SympohyConfig
from .core import (
    extract_acceptance_set,
    merge_gate_allows_merge,
    next_retry_action,
    parse_review_json,
    validate_commit_subject,
)
from .github import Issue, comment, fetch_issue, list_candidate_issues, set_issue_state


def ensure_worktree(issue: Issue, config: SympohyConfig) -> Path:
    worktree = config.worktree_root / f"issue-{issue.number}"
    branch = f"issue-{issue.number}-sympohy"
    if worktree.exists():
        return worktree

    worktree.parent.mkdir(parents=True, exist_ok=True)
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


def run_issue(issue_ref: str, config: SympohyConfig) -> int:
    issue = fetch_issue(issue_ref)
    acceptance = extract_acceptance_set(issue.body, issue.comments)
    if acceptance is None:
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
    log_dir = config.run_log_root / f"issue-{issue.number}"
    log_dir.mkdir(parents=True, exist_ok=True)

    set_issue_state(
        issue_ref,
        current_labels=issue.labels,
        status="sympohy:running",
        phase="implement",
    )

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
        log_path=log_dir / "plan.json",
    )

    for index, step in enumerate(_logical_steps(plan), start=1):
        set_issue_state(
            issue_ref,
            current_labels=("sympohy:running", "sympohy:phase:implement"),
            status="sympohy:running",
            phase="implement",
            cwd=worktree,
        )
        _codex_text(
            [
                f"Implement logical step {index} for SIFTQ issue #{issue.number}.",
                json.dumps(step, ensure_ascii=False),
                "Use normal Codex user config and repository rules.",
            ],
            cwd=worktree,
            log_path=log_dir / f"implement-{index}.log",
        )
        if _run_hooks(config.hooks, config.retry_max_attempts, worktree, log_dir) != 0:
            _block(
                issue_ref,
                phase="hooks",
                failed_command="; ".join(config.hooks),
                attempts=config.retry_max_attempts,
                cause="verification hooks still failed after retries",
                run_log_path=log_dir,
                cwd=worktree,
            )
            return 2
        subject = f"#{issue.number} feat(sympohy): implement logical step {index}"
        if not validate_commit_subject(subject):
            raise ValueError(f"invalid generated commit subject: {subject}")
        subprocess.check_call(["git", "add", "-A"], cwd=worktree)
        subprocess.check_call(["git", "commit", "-m", subject], cwd=worktree)

    branch = subprocess.check_output(
        ["git", "branch", "--show-current"],
        cwd=worktree,
        text=True,
    ).strip()
    subprocess.check_call(["git", "push", "-u", "origin", branch], cwd=worktree)
    subprocess.check_call(["gh", "pr", "create", "--draft", "--fill"], cwd=worktree)
    review_result = _review_fix_loop(issue_ref, issue, config, worktree, log_dir)
    if review_result != 0:
        return review_result

    final = _codex_json(
        [
            "Act as final verifier. Return JSON with boolean "
            "acceptance_criteria_satisfied, boolean definition_of_done_satisfied, "
            "and merge_recommendation set to merge or block.",
            f"Issue #{issue.number}",
        ],
        cwd=worktree,
        log_path=log_dir / "final-verifier.json",
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
        )
        return 2

    subprocess.check_call(["gh", "pr", "ready"], cwd=worktree)
    subprocess.check_call(["gh", "pr", "checks", "--watch"], cwd=worktree)
    subprocess.check_call(["gh", "pr", "merge", "--squash", "--delete-branch"], cwd=worktree)
    subprocess.check_call(["git", "worktree", "remove", str(worktree)])
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
) -> int:
    for command in hooks:
        attempts = 0
        while True:
            attempts += 1
            log_path = log_dir / f"hook-{attempts}.log"
            with log_path.open("w", encoding="utf-8") as log:
                result = subprocess.run(
                    shlex.split(command),
                    cwd=cwd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
            if result.returncode == 0:
                break
            if next_retry_action(attempts, retry_max_attempts) == "block":
                return result.returncode
            _codex_text(
                [
                    f"The hook failed: {command}",
                    f"Inspect {log_path} and fix the cause, then stop.",
                ],
                cwd=cwd,
                log_path=log_dir / f"hook-fix-{attempts}.log",
            )
    return 0


def _review_fix_loop(
    issue_ref: str,
    issue: Issue,
    config: SympohyConfig,
    cwd: Path,
    log_dir: Path,
) -> int:
    for round_index in range(1, config.review_max_rounds + 1):
        set_issue_state(
            issue_ref,
            current_labels=("sympohy:running", "sympohy:phase:review"),
            status="sympohy:running",
            phase="review",
            cwd=cwd,
        )
        review_json = _codex_text(
            [
                "Review this PR adversarially. Return machine-parseable JSON "
                "with findings: [{severity, summary, status}]. Severities are "
                "critical, high, medium, low, info.",
                f"Issue #{issue.number}",
            ],
            cwd=cwd,
            log_path=log_dir / f"review-{round_index}.json",
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
            )
            return 2
        set_issue_state(
            issue_ref,
            current_labels=("sympohy:running", "sympohy:phase:fix"),
            status="sympohy:running",
            phase="fix",
            cwd=cwd,
        )
        _codex_text(
            [
                "Fix these blocking review findings and stop after edits.",
                review_json,
            ],
            cwd=cwd,
            log_path=log_dir / f"fix-{round_index}.log",
        )
        subject = f"#{issue.number} fix(sympohy): resolve review finding {round_index}"
        subprocess.check_call(["git", "add", "-A"], cwd=cwd)
        subprocess.check_call(["git", "commit", "-m", subject], cwd=cwd)
        subprocess.check_call(["git", "push"], cwd=cwd)
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
) -> None:
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
            f"- failed command: {failed_command}\n"
            f"- attempts: {attempts}\n"
            f"- cause: {cause}\n"
            f"- run log path: {run_log_path}\n"
        ),
        cwd=cwd,
    )


def _codex_json(prompts: Sequence[str], *, cwd: Path, log_path: Path) -> Mapping[str, object]:
    output = _codex_text(prompts, cwd=cwd, log_path=log_path)
    payload = json.loads(output)
    if not isinstance(payload, Mapping):
        raise ValueError("Codex JSON output must be an object")
    return payload


def _codex_text(prompts: Sequence[str], *, cwd: Path, log_path: Path) -> str:
    prompt = "\n\n".join(prompts)
    output = subprocess.check_output(["codex", "exec", prompt], cwd=cwd, text=True)
    log_path.write_text(output, encoding="utf-8")
    return output


def _logical_steps(plan: Mapping[str, object]) -> list[Mapping[str, object]]:
    steps = plan.get("logical_steps", [])
    if not isinstance(steps, list) or not steps:
        raise ValueError("plan JSON must contain non-empty logical_steps")
    return [step for step in steps if isinstance(step, Mapping)]


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
