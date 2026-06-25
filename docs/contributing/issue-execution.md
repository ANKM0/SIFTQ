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
    - id: design:development-flow
      relation: depends_on
      semantic: automation
    - id: design:sympohy-run-lifecycle-state
      relation: depends_on
      semantic: automation
    - id: design:sympohy-stale-run-recovery
      relation: depends_on
      semantic: automation
    - id: design:sympohy-terminal-resume-review-hardening
      relation: depends_on
      semantic: automation
    - id: design:codex-configuration-memo
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

## Codex Model Roles

`sympohy` passes an explicit Codex model and reasoning effort for each automated
Codex role. The checked-in defaults use only models visible in the current local
Codex account model catalog: `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, and
`gpt-5.3-codex-spark`. `gpt-5.5-pro` is intentionally not configured because it
is not available in that catalog.

| Role | Model | Reasoning | Used for |
| --- | --- | --- | --- |
| `default` | `gpt-5.5` | `high` | Fallback for unclassified Codex calls |
| `triage` | `gpt-5.4-mini` | `medium` | Lightweight issue classification or future triage calls |
| `planning` | `gpt-5.4-mini` | `medium` | Documentation artifact decisions and logical implementation plan |
| `implementation` | `gpt-5.4` | `medium` | Logical-step implementation |
| `fix` | `gpt-5.4` | `medium` | Hook, review, and final-verifier fixes |
| `review` | `gpt-5.5` | `high` | Adversarial PR review |
| `merge_readiness` | `gpt-5.5` | `xhigh` | Final verifier and merge recommendation |

Configure these values in `.sympohy/config.yaml` with
`codex_model_<role>` and `codex_reasoning_<role>` keys. The runner still uses
normal Codex user config and repository rules; it only adds `--model` and
`model_reasoning_effort` for the selected role.

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
task ai:sympohy:systemd:start
task ai:sympohy:systemd:stop
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
- `sympohy:phase:finalize`

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

Closed legacy tasks become `sympohy:done` and `sympohy:phase:finalize`. Blocked
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

Install and start the systemd user service:

```bash
task ai:sympohy:systemd:install
```

Start or stop the installed service:

```bash
task ai:sympohy:systemd:start
task ai:sympohy:systemd:stop
```

Check status and recent logs:

```bash
task ai:sympohy:systemd:status
```

The watcher is a foreground daemon. When installed under systemd, the service
keeps the daemon running and restarts it if it exits unexpectedly. The daemon
polls GitHub once per `watch_poll_interval_seconds` and selects open issues
that do not have any of
`sympohy:pending`, `sympohy:running`, `sympohy:blocked`, or `sympohy:done`.
It also reselects `sympohy:running` issues whose run state is stale because the
worker pid is missing or dead, the state file is missing, or the heartbeat has
expired. Fresh issues start through normal triage, while stale running issues
are routed through resume handling so they are not excluded permanently.

The checked-in conservative profile keeps `max_workers: 3` workers active.
When a worker exits, the
next poll reaps it and fills the open slot from the issue queue. Each worker
uses an independent `.sympohy/worktrees/issue-<number>` worktree and issue
branch.

During stale-run recovery, `sympohy` reloads the saved implementation plan when
available and compares it with logical-step commits already present in the issue
worktree. A clean recovered worktree continues from the next missing logical
step. If all logical steps are already committed, recovery skips implementation
and proceeds to branch update push, existing draft PR verification, review, and
merge readiness.

If the runner receives `SIGTERM`, `SIGINT`, or `SIGHUP`, it records the current
phase, logical step progress, and signal name in `state.json` with status
`interrupted` before exiting when possible. The next watcher or manual resume
treats that state as resumable work rather than leaving a misleading fresh
`running` state behind. If the interrupted Codex step left uncommitted changes,
implementation recovery reuses those worktree changes for the recorded logical
step instead of starting from scratch.

## Hooks, Review, and Merge

Hooks are configured in `.sympohy/config.yaml`. The initial final hook is:

```bash
task ci
```

The checked-in conservative profile uses `ci_retry_max_attempts: 10`,
`review_max_rounds: 3`, and `final_verifier_fix_max_attempts: 2` to avoid
long blind retry loops during local watcher operation. The development-flow
compatibility values remain `ci_retry_max_attempts: 50` and
`review_max_rounds: 10` for operators that intentionally want the full loop
budget.

Hook failures trigger a Codex fix attempt and rerun, up to
`ci_retry_max_attempts`. If the hook still fails, `sympohy` blocks the issue
and comments with the phase, failed command, attempts, cause summary, and run
log path.

After branch creation, `sympohy` pushes the issue branch and creates the main
target draft PR before implementation work continues. When the branch has no
diff yet, the runner may create an empty traceability commit using the repository
commit message format so GitHub can open the draft PR. Later implementation,
hook fix, review fix, and final verifier fix commits are pushed to the same PR
branch.

The draft PR body must start from `.github/pull_request_template.md` so required
verification prompts, including Matrix browser storage reload smoke evidence,
remain visible on automation-created PRs.
For #59 browser-only work governed by ADR 0018, Tauri WebView reload / F5 and
`task tauri:dev` app restart persistence checks are not applicable; if stale
issue history or review text adds those result lines, the PR body must mark them
N/A with an ADR 0018 note instead of leaving them pending.

After `task ci` succeeds, `sympohy` verifies that the draft PR still exists,
runs an adversarial review Codex pass that must return machine-readable JSON,
and repeats fix/review up to `review_max_rounds` until there are no `critical`,
`high`, or `medium` findings.
Review results are posted to the PR so blocking findings and fix status are
traceable.

Before adversarial review starts, `sympohy` runs a dedicated mergeability gate
against the PR base branch. If the PR conflicts with `main`, the runner may
attempt one pre-review auto-fix before consuming review or fix rounds. This
attempt includes taking the base branch, using Codex to resolve conflicts when
needed, confirming no conflict markers remain, running `task ci`, and pushing
the repaired branch. Only when this pre-review auto-fix fails does the runner
block the issue. The resulting block comment includes the PR number, base/head,
a concise conflict summary, and the recommended next step.

Automation-created PRs must include issue traceability, summary, and validation
sections in the PR body. If an existing PR body is empty, or those required
metadata sections are missing, `sympohy` backfills the minimum metadata from
the PR template before review continues instead of blocking immediately.

Before merge, a final verifier Codex pass must return JSON confirming AC/DoD
satisfaction and recommending `merge` or `block`. `merge` responses must include
an empty `findings[]` array. `block` responses must include a non-empty
`findings[]` array whose entries provide `kind`, `summary`, `evidence`, and
`suggested_fix` fields so the runner can feed the result into automated fixing.
Each verifier attempt is persisted as `final-verifier-<attempt>.json`; the
runner also refreshes `final-verifier.json` with the latest attempt for
compatibility with existing tooling.
`kind` is one of `acceptance_criteria`, `definition_of_done`, `verification`,
`reviewability`, or `other`. Valid non-empty verifier findings move the issue
to `sympohy:phase:fix` with `fix_source=final_verifier`, up to
`final_verifier_fix_max_attempts` configured in `.sympohy/config.yaml` (default
`2`). Setting `final_verifier_fix_max_attempts: 0` disables automated
final-verifier fixes; valid retry findings then block the issue immediately.
After hooks pass for a final-verifier fix, `sympohy` commits and pushes the
fix, reruns adversarial review, and only then reruns the final verifier.
Missing, empty, or schema-invalid block findings add `sympohy:blocked` instead
of starting a fix. If the final verifier still reports blocking findings after
the configured fix attempts, `sympohy` blocks the issue instead of starting
another fix.
`sympohy` then marks the PR ready, waits for GitHub checks, and squash merges
through the PR with branch deletion when the final gate allows merge.

Successful merge adds `sympohy:done`, closes the issue, removes the issue
worktree, and keeps `.sympohy/runs/*` logs. Blocked runs keep both the worktree
and run logs for manual investigation.
