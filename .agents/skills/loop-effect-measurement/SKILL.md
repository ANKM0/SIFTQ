---
name: loop-effect-measurement
description: Run the loop evaluation harness when changing loop definitions, verification, guards, or agent prompts under .taqt/loops/ or .taqt/scripts/loop/.
---

# Loop Effect Measurement

Load this skill for an issue that changes any path under these directories:

- `.taqt/loops/`
- `.taqt/scripts/loop/`

These paths cover loop definitions, verification, guards, and agent prompts.
Do not use `refacta_loop.md`; it is gitignored and is not part of the target.

## T2: Defect Injection

Run from the repository root on a fixed, clean baseline:

```bash
PYTHONPATH=.taqt/scripts uv run python -m loop_eval.defect_injection \
  --repo . --mutant-root eval/gold/loop-mutants
```

Before injecting mutants, confirm the clean checkout passes the commands used by
arm B: `git diff --check`, `task setup:frontend:ci`, `task ci:lint`,
`task ci:lint:python`, `task ci:typecheck`, `task ci:test:unit`, and
`task ci:test:e2e`.

Adopt the change when arm B's catch rate is higher than arm A's,
`a_missed_b_caught` is higher than `a_caught_b_missed`, and the clean checks
have no false failures. Record the emitted JSON and the mutant count.

## T3: Paired Replay

Run each gold task with the same commit and workspace for both arms. Replace
`<name>` and `<ISSUE>` with the replay spec and task name:

```bash
PYTHONPATH=.taqt/scripts uv run python -m loop_eval.replay \
  --spec eval/gold/loop-tasks/<name>.yaml \
  --task .taqt/tasks/<ISSUE>.yaml \
  --workspace . --runs-root .taqt/runs
```

Repeat each task at least 3 times and report the point estimate and `n`.
Adopt the change when closure rate does not decrease and escaped-defect rate
does not increase against the previous arm on the same task set and baseline
commit. Do not claim statistical significance from a small sample.
