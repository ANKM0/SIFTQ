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

This note records the current `sympohy:running` watcher behavior before adding
stale-run detection and resume logic for issue #82.

## Candidate Selection

`scripts/sympohy/github.py` lists open GitHub issues with:

```text
gh issue list --state open --limit <limit> --json number,title,state,labels
```

It then delegates filtering to `scripts/sympohy/core.py:is_candidate_issue`.
The current predicate accepts only open issues without any status label in
`STATUS_LABELS`.

As a result, an issue with `sympohy:running` is excluded even when it also has a
specific phase label such as `sympohy:phase:implement`. The watcher never
reconsiders that issue unless the status label is changed externally.

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
run. The document includes the current phase, worker pid, heartbeat timestamp,
branch and worktree metadata, plan reference, and last known progress.

The heartbeat is refreshed while Codex and hook subprocesses are still running,
which gives stale-run inspection a durable signal separate from GitHub labels.

## Watcher Resume Routing

The watcher now keeps fresh issue starts and stale-run recovery separate. Fresh
open issues still receive `sympohy:pending` and `sympohy:phase:triage` before a
`run` worker starts. Stale `sympohy:running` issues are dispatched to the
`resume` entrypoint instead, preserving their running labels and phase context
for resume handling.

## Resume Point Resolution

`resume` resolves a coarse resume point from the current `sympohy` labels before
restarting automation. `sympohy:phase:triage` and missing phase context map to
`planning`; `sympohy:phase:implement` and `sympohy:phase:hooks` map to
`implement`; and `sympohy:phase:review`, `sympohy:phase:fix`, and
`sympohy:phase:merge` map to `push_pr`.

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
the worktree still has uncommitted changes after those commits, recovery treats
those changes as the next logical step and resumes with hooks and commit instead
of invoking Codex for that same step again.

## Existing Tests

`tests/sympohy/sympohy_core_test.py` covers stale-running inspection and
candidate selection for `sympohy:running` issues, plus status/phase replacement
through `transition_labels`.

`tests/sympohy/sympohy_runner_test.py` covers watcher dispatch for both fresh
issues and stale `sympohy:running` issues.

`tests/sympohy/sympohyWorkflowContracts.test.ts` contains string-level
watcher contracts for stale-running inspection, run state persistence, and the
resume entrypoint.
