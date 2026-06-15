---
codd:
  node_id: design:issue-82-stale-running-inspection
  type: design
  status: draft
  depends_on:
    - id: design:sympohy-ticket-driven-ai-runner-adr
      relation: depends_on
      semantic: decision
    - id: design:sympohy-issue-execution
      relation: depends_on
      semantic: automation
---

# Issue 82 Stale Running Inspection

## Scope

This note records the current `sympohy:running` watcher behavior, stale-run
detection, resume routing, and phase lifecycle boundaries for issue #82.

## Logical Step 1 Boundary Map

This inspection covers the current watcher, CLI, lock, run-state, heartbeat,
label, worktree, and test code paths. The important boundary is that GitHub
labels are the externally visible issue lifecycle, while `.sympohy/runs` and
per-issue worktrees are the local execution lifecycle.

- Watcher boundary: `runner.py:watch` asks `github.py:list_candidate_issues`
  for open issues, then decides only between fresh worker start and stale-run
  resume routing. Fresh issues are moved to `sympohy:pending` and
  `sympohy:phase:triage` before spawning `run`. Issues already carrying
  `sympohy:pending` or `sympohy:running` are never relabeled by the watcher; if
  stale, they are spawned through `resume`.
- CLI boundary: `cli.py` exposes `run` for fresh execution, `resume` for
  interrupted or stale execution, `refine` for AC/DoD inspection, `watch` for
  polling, `labels-sync` for GitHub label definitions, and `doctor` for local
  runner prerequisites. Taskfile entrypoints call these Python commands through
  `uv run python -m scripts.sympohy`.
- Candidate-selection boundary: `core.py:is_candidate_issue` accepts open
  issues without a `sympohy` status label, and only reselects
  `sympohy:pending` or `sympohy:running` issues when
  `inspect_running_issue` reports stale state. `sympohy:blocked` and
  `sympohy:done` are terminal for watcher selection.
- Lock boundary: `runner.py:_IssueRunLock` owns one
  `.sympohy/runs/issue-<number>/run.lock` per issue. It rejects concurrent
  active runs, permits takeover only when lock/state metadata agree that the
  previous owner is stale, and prevents an old writer from updating state after
  takeover.
- Run-state boundary: `runner.py:_RunStateWriter` owns
  `.sympohy/runs/issue-<number>/state.json`, including `run_id`, phase, status,
  pid, heartbeat, lock metadata, branch, worktree, plan reference,
  `last_known_progress`, and `last_recovery`. This state is the local source of
  truth for resume point resolution when present.
- Heartbeat boundary: long-running Codex, hook, GitHub check, and merge
  subprocesses refresh state through heartbeat callbacks. Stale inspection
  treats missing state, corrupt state, missing phase, missing pid, dead pid,
  missing heartbeat, and expired heartbeat as recoverable stale signals.
- Label boundary: `core.py:transition_labels` keeps at most one known
  `sympohy` status label and one known phase label while preserving non-Sympohy
  labels. `github.py:set_issue_state` fetches latest labels before applying
  remove/add diffs, so label transitions are centralized.
- Phase lifecycle boundary: `run_issue` starts at triage, moves to implement
  after AC/DoD is complete, writes hooks progress for each logical step, then
  advances through review, fix, and merge. Blocking paths call `_block`, which
  marks `sympohy:blocked`, preserves logs/worktrees, and comments with the
  failed phase and cause. Successful merge marks `sympohy:done`, closes the
  issue, removes the issue worktree, and keeps run logs.
- Worktree boundary: `ensure_worktree` creates or recovers
  `.sympohy/worktrees/issue-<number>` on branch `issue-<number>-sympohy`.
  Fresh runs refuse existing local or remote issue branches; recovery requires
  the expected branch and blocks if neither local nor remote state can be
  recovered safely.
- Resume boundary: `resume_issue` resolves terminal, planning, implement,
  hooks, review, fix, and merge points from state first, then phase labels.
  Terminal blocked/done states are reconciled without restarting work. Planning
  restarts without recovery mode, implementation reloads `plan.json` and
  inspects logical-step commits, hooks resumes the saved current logical step,
  and late phases use phase-specific safety checks.
- Test boundary: Python unit tests cover candidate selection, stale inspection,
  resume routing, lock takeover, run-state persistence, worktree recovery,
  implementation recovery, terminal reconciliation, and late-phase dirty
  worktree blocking. The TypeScript workflow contract test keeps the Taskfile,
  CLI, stale-running, run-state, and Codex-config contracts visible in the
  frontend test suite.

## Candidate Selection

`scripts/sympohy/github.py` lists open GitHub issues with:

```text
gh issue list --state open --limit <limit> --json number,title,state,labels
```

It then delegates filtering to `scripts/sympohy/core.py:is_candidate_issue`.
The current predicate accepts open issues without any `sympohy` status label as
fresh work. It excludes terminal `sympohy:blocked` and `sympohy:done` issues,
and it only reselects `sympohy:pending` or `sympohy:running` issues when
`inspect_running_issue` reports stale local run state.

## Label Handling

`transition_labels` removes all known `sympohy` status labels and all known
phase labels before adding the requested status and phase. This preserves
non-sympohy labels while enforcing at most one active status and one active
phase.

`scripts/sympohy/github.py:set_issue_state` computes the difference between the
current label set and the desired label set, then calls `gh issue edit` with
`--remove-label` and `--add-label` as needed.

## Run State Storage

The configuration already defines `run_log_root` as `.sympohy/runs`, and
`runner.py` writes Codex output and hook output below
`.sympohy/runs/issue-<number>/`.

The runner now writes `.sympohy/runs/issue-<number>/state.json` for each issue
run. The document includes the shared `run_id`, current phase, worker pid,
heartbeat timestamp, lock metadata, branch and worktree metadata, plan
reference, and last known progress.

The heartbeat is refreshed while Codex and hook subprocesses are still running,
which gives stale-run inspection a durable signal separate from GitHub labels.
The stale threshold is configured by `stale_status_after_minutes` and validated
as a positive value by `sympohy doctor`.

## Watcher Resume Routing

The watcher now keeps fresh issue starts and stale-run recovery separate. Fresh
open issues still receive `sympohy:pending` and `sympohy:phase:triage` before a
`run` worker starts. Stale `sympohy:running` issues are dispatched to the
`resume` entrypoint instead, preserving their running labels and phase context
for resume handling.

## Resume Point Resolution

`resume` resolves a coarse resume point from `state.json.phase` when run state
exists. GitHub phase labels are treated as fallback bootstrap input only when
state is missing or corrupt, and resume corrects stale phase labels from the
resolved state phase before continuing. `triage` maps to `planning`,
`implement` and `hooks` map to implementation recovery, while `review`, `fix`,
and `merge` resume through phase-specific late-phase handlers.

Terminal status labels are not restarted. `sympohy:blocked` resolves to the
`blocked` terminal point, and `sympohy:done` resolves to the `completed`
terminal point.

## Implement-Phase Recovery

When stale-run recovery re-enters implementation, the runner first attempts to
load the existing `.sympohy/runs/issue-<number>/plan.json`. A valid saved plan is
reused instead of asking Codex to generate a new plan, keeping logical step
numbering stable across restarts.

The runner infers completed work from local Git state. Commit subjects matching
`#<issue> feat(sympohy): implement logical step <n>` count as completed only for
the contiguous prefix of logical steps on top of the configured base branch. If
the worktree still has uncommitted changes after those commits, recovery blocks
and leaves the dirty worktree for operator inspection instead of guessing that
the changes belong to the next logical step.

If the recovered worktree is clean, the same contiguous commit prefix determines
the next action. A clean worktree with incomplete implementation resumes Codex
at the next missing logical step. A clean worktree whose implementation commits
already cover the saved plan skips implementation and proceeds directly to
branch push and draft PR creation.

## Existing Tests

`tests/sympohy/sympohy_core_test.py` covers stale-running inspection and
candidate selection for `sympohy:running` issues, plus status/phase replacement
through `transition_labels`.

`tests/sympohy/sympohy_runner_test.py` covers watcher dispatch for both fresh
issues and stale `sympohy:running` issues, plus dirty and clean implementation
resume decisions.

`tests/sympohy/sympohyWorkflowContracts.test.ts` contains string-level
watcher contracts for stale-running inspection, run state persistence, and the
resume entrypoint.
