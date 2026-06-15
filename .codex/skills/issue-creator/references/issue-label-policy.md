# SIFTQ Issue Label Policy

Use these rules when drafting or creating SIFTQ issues for `sympohy`.

## Manual Queue Labels

Apply both labels to a new issue that is ready for `sympohy` triage:

- `sympohy:pending`
- `sympohy:phase:triage`

Use `sympohy:pending` to mark an issue as queued for automation. Use
`sympohy:phase:triage` to tell `sympohy` that the next step is AC/DoD inspection
and planning.

## Automation-Owned Labels

Do not manually apply these labels to new issues:

- `sympohy:running`
- `sympohy:blocked`
- `sympohy:done`
- `sympohy:phase:implement`
- `sympohy:phase:hooks`
- `sympohy:phase:review`
- `sympohy:phase:fix`
- `sympohy:phase:finalize`

`sympohy` owns transitions after triage starts. It keeps one status label and
one phase label on managed issues, replacing stale workflow labels as the issue
moves through implementation, hooks, review, fix, and finalize phases.

## Labeling Rules

- Keep non-workflow labels such as `bug`, `documentation`, or release labels
  when the user requests them or repository context clearly requires them.
- Do not add legacy `ai:*`, `takt:*`, or `taqt:*` labels.
- If the issue is only a draft and should not be picked up by automation, omit
  `sympohy:pending` until the user confirms it is ready.
- If the issue lacks complete AC/DoD and is intended for implementation, keep it
  as a draft instead of queueing it.
