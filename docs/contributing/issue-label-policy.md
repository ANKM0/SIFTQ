---
codd:
  node_id: design:issue-label-policy
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:sympohy-issue-execution
      relation: depends_on
      semantic: workflow
  depended_by: []
---

# Issue Label Policy

SIFTQ uses GitHub issue labels to hand work to `sympohy` and to record the
automation phase. Human operators may queue work, but automation owns runtime
state transitions.

## Manual Queue Labels

Use these labels together when manually queuing an open issue for `sympohy`:

- `sympohy:pending`: marks the issue as queued for a future `sympohy` run.
- `sympohy:phase:triage`: starts the queued issue at the AC/DoD and
  prerequisite-check phase.

Only apply `sympohy:pending` when the issue is ready for automated inspection.
If an issue has no `sympohy:*` status label, the watcher may also pick it up as
fresh work and place it into the same triage flow.

Keep exactly one `sympohy:phase:*` label on a managed issue. Manual queueing
should use `sympohy:phase:triage`; later phase labels are set by automation as
the issue moves through implementation, hooks, review, fix, and finalization.

## Labels Not Applied Manually

Do not manually add these status labels:

- `sympohy:running`
- `sympohy:blocked`
- `sympohy:done`

These labels are automation-owned state. `sympohy:running` is used while a
worker is active or recoverable, `sympohy:blocked` records missing input or
repeated automation failure with a comment, and `sympohy:done` records completed
merge and issue closure. Manual changes to those labels can hide work from the
watcher, skip recovery behavior, or make issue history disagree with the run
logs.

To request automated work manually, add `sympohy:pending` with
`sympohy:phase:triage` instead of adding runtime status labels.
