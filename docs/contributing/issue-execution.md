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

`sympohy` replaces the older TAKT/taqt task workflow. Mentions of `takt`/`taqt`
below are kept strictly as historical migration context.
Tracked configuration and
systemd templates live in `.sympohy/`; generated issue worktrees and run logs
live in `.sympohy/worktrees/` and `.sympohy/runs/`, which are ignored by Git.

## Requirements

Run `sympohy` from a trusted local checkout with the normal SIFTQ development
tooling installed:

- `git`, `gh`, `aqua`, `uv`, `pnpm`, and `task`.
- An authenticated `gh` session that can read and update issues, labels, pull
  requests, and checks for `ANKM0/SIFTQ`.
- A normal Codex CLI setup with the user's `HOME`, `CODEX_HOME`, repository
  rules, and repository skills available.
- A clean enough Git worktree for the command being run. Generated sympohy
  worktrees are separate from the operator's checkout.

Do not run Codex with flags that ignore user configuration or repository rules.
The runner depends on those settings for command permissions and repo-specific
workflow instructions.

## Setup

Install repository tools and dependencies first:

```bash
aqua install
task setup
```

Validate only the sympohy prerequisites and configuration:

```bash
task setup:sympohy
task ai:sympohy:doctor
```

`task setup:sympohy` checks local prerequisites for the repository runner.
`task ai:sympohy:doctor` validates sympohy config, labels, systemd templates,
Codex availability, hooks, and GitHub prerequisites.

The local CI gate also runs the sympohy checks:

```bash
task ci:sympohy
task ci
```

## Usage

Inspect an issue for the latest complete AC/DoD set without implementation:

```bash
task ai:sympohy:refine -- '#73'
```

Run one issue through the automation:

```bash
task ai:sympohy -- '#73'
```

Resume a stale or interrupted run:

```bash
task ai:sympohy:resume -- '#73'
```

Use quotes around `#73` in shells where `#` starts a comment. The underlying
CLI also accepts the issue token passed through Taskfile as a positional
argument.

## Common Workflow Commands

These are the common operator commands for issue execution:

```bash
task setup:sympohy
task ai:sympohy:doctor
task ai:sympohy:labels:sync
task ai:sympohy:refine -- '#73'
task ai:sympohy -- '#73'
task ai:sympohy:resume -- '#73'
task ai:sympohy:migrate -- --dry-run '#73'
task ai:sympohy:migrate -- '#73'
task ai:sympohy:migrate -- --all
task ai:sympohy:watch
task ai:sympohy:systemd:install
task ai:sympohy:systemd:status
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
`ai:*` labels from the repository label definitions. Before deleting legacy
label definitions, it migrates any issues that still carry `ai:*`, `takt:*`, or
`taqt:*` task labels so issue-level workflow state is not lost.

New issue execution state must use `sympohy:*` labels only. Do not add new
TAKT/taqt labels or directories.

## Migration

Migration is label-only. It preserves issue title, body, comments, assignees,
milestone, and link relationships because it removes only legacy workflow labels
and applies equivalent `sympohy:*` status and phase labels. Existing
non-workflow labels are kept.

Inspect a single issue migration without writing changes:

```bash
task ai:sympohy:migrate -- --dry-run '#73'
```

Migrate a single legacy task issue:

```bash
task ai:sympohy:migrate -- '#73'
```

Migrate every issue that still has legacy `ai:*`, `takt:*`, or `taqt:*` task
labels with:

```bash
task ai:sympohy:migrate -- --all
```

Limit bulk migration while testing:

```bash
task ai:sympohy:migrate -- --all --limit 10
```

Closed legacy tasks become `sympohy:done` and `sympohy:phase:merge`. Blocked
tasks become `sympohy:blocked` and `sympohy:phase:triage`. In-progress workflow
labels map to the matching `implement`, `hooks`, `review`, or `fix` phase where
that intent is represented by sympohy. Ready or queued legacy tasks start as
`sympohy:pending` in `triage` so sympohy can re-check the latest AC/DoD before
implementation.

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

Run the watcher in the foreground:

```bash
task ai:sympohy:watch
```

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
