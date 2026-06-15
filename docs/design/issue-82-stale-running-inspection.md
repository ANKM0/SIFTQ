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

## Existing Tests

`tests/sympohy/sympohy_core_test.py` covers candidate exclusion for an open
issue with `sympohy:running` and covers status/phase replacement through
`transition_labels`.

`tests/sympohy/sympohyWorkflowContracts.test.ts` contains a string-level
watcher contract that asserts managed issues are excluded by checking for
`not names.intersection(STATUS_LABELS)`.

These tests describe the current baseline. The stale-run implementation should
replace the blanket running exclusion with explicit stale detection and resume
selection tests.
