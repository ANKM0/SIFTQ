---
codd:
  node_id: design:sympohy-issue-execution
  type: design
  status: draft
  depends_on:
    - id: design:sympohy-ticket-driven-ai-runner-adr
      relation: depends_on
      semantic: decision
    - id: design:taskfile-command-runner-adr
      relation: depends_on
      semantic: automation
    - id: design:branch-strategy
      relation: depends_on
      semantic: workflow
    - id: design:commit-message-format
      relation: depends_on
      semantic: workflow
  depended_by:
    - id: design:issue-82-stale-running-inspection
      relation: depends_on
      semantic: automation
---

# sympohy Issue Execution

SIFTQ uses `sympohy` as repository-local development tooling for GitHub
Issue-driven implementation. It is not part of the SIFTQ application runtime
and is not listed in `package.json` or installed as a frontend dependency.

`sympohy` runs from the repository through Taskfile:

```bash
task setup:sympohy
task ai:sympohy:doctor
task ai:sympohy -- '#74'
task ai:sympohy:refine -- '#74'
```

## Labels

`sympohy` owns these status labels:

- `sympohy:pending`
- `sympohy:running`
- `sympohy:blocked`
- `sympohy:done`

It also owns exactly one active phase label per managed issue:

- `sympohy:phase:triage`
- `sympohy:phase:implement`
- `sympohy:phase:hooks`
- `sympohy:phase:review`
- `sympohy:phase:fix`
- `sympohy:phase:merge`

Synchronize labels with:

```bash
task ai:sympohy:labels:sync
```

The sync command creates or updates `sympohy:*` labels and removes legacy
`ai:*` labels from the repository label definitions. New issue execution state
must use `sympohy:*` labels only.

## Refinement

`sympohy` reads the issue body and issue comments, then uses the latest complete
AC/DoD set it can find. A complete set must include both an AC section and a
DoD section with checklist or bullet items.

If a complete AC/DoD set is missing, `sympohy` does not implement the issue. It
adds `sympohy:blocked` and `sympohy:phase:triage`, then comments with the
blocked reason.

## Watcher

The watcher is intended for trusted local environments with authenticated
`gh`, local `git`, Taskfile, and normal Codex CLI configuration.

Install the systemd user timer:

```bash
task ai:sympohy:systemd:install
```

Check status and recent logs:

```bash
task ai:sympohy:systemd:status
```

The timer runs once per minute. It selects open issues that do not have any of
`sympohy:pending`, `sympohy:running`, `sympohy:blocked`, or `sympohy:done`.
It also reselects `sympohy:running` issues whose run state is stale because the
worker pid is missing or dead, the state file is missing, or the heartbeat has
expired. Fresh issues start through normal triage, while stale running issues
are routed through resume handling so they are not excluded permanently.

The watcher starts at most ten workers, and each worker uses an independent
`.sympohy/worktrees/issue-<number>` worktree and issue branch.

During stale-run recovery, `sympohy` reloads the saved implementation plan when
available and compares it with logical-step commits already present in the issue
worktree. A clean recovered worktree continues from the next missing logical
step. If all logical steps are already committed, recovery skips implementation
and proceeds to branch push and draft PR creation.

## Hooks, Review, and Merge

Hooks are configured in `.sympohy/config.yaml`. The initial final hook is:

```bash
task ci
```

Hook failures trigger a Codex fix attempt and rerun, up to three attempts. If
the hook still fails, `sympohy` blocks the issue and comments with the phase,
failed command, attempts, cause summary, and run log path.

After `task ci` succeeds, `sympohy` creates a draft PR, runs an adversarial
review Codex pass that must return machine-readable JSON, and repeats fix/review
up to five rounds until there are no `critical`, `high`, or `medium` findings.
Review results are posted to the PR so blocking findings and fix status are
traceable.

Before merge, a final verifier Codex pass must return JSON confirming AC/DoD
satisfaction and recommending merge. `sympohy` then marks the PR ready, waits
for GitHub checks, and squash merges through the PR with branch deletion.

Successful merge adds `sympohy:done`, closes the issue, removes the issue
worktree, and keeps `.sympohy/runs/*` logs. Blocked runs keep both the worktree
and run logs for manual investigation.
