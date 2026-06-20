---
codd:
  node_id: design:sympohy-ticket-driven-ai-runner-adr
  type: design
  status: accepted
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:taskfile-command-runner-adr
      relation: depends_on
      semantic: automation
  depended_by:
    - id: design:ci-cd-foundation
      relation: depends_on
      semantic: automation
    - id: design:sympohy-issue-execution
      relation: depends_on
      semantic: decision
    - id: design:sympohy-run-lifecycle-state
      relation: depends_on
      semantic: decision
    - id: design:sympohy-stale-run-recovery
      relation: depends_on
      semantic: decision
---

# ADR 0013: sympohy for Ticket-Driven AI Runner

## Status

Accepted.

## Context

SIFTQ needs a GitHub Issue-driven automation path that can refine AC/DoD,
implement scoped changes, run repository hooks, create PRs, run adversarial
review and fix loops, wait for GitHub checks, squash merge, close issues, and
retain logs.

Issue #74 raises the requirement to run up to ten issues in parallel, isolate
each issue in a `git worktree`, manage state through GitHub labels, install a
systemd user service, and keep the runner under direct repository control.

The runner remains development operations tooling. It must not become a SIFTQ
application runtime dependency or affect the React/Vite application boundary.

## Decision

SIFTQ adopts `sympohy` as a Python, repository-local ticket-driven AI runner.

`sympohy` lives under `scripts/sympohy` and is invoked through Taskfile with
`uv run python -m scripts.sympohy ...`. The repository tracks `.sympohy` config
and systemd user unit templates, while generated worktrees and run logs stay
local.

GitHub state is represented by `sympohy:*` labels. Status labels are
`pending`, `running`, `blocked`, and `done`. Phase labels are `triage`,
`implement`, `hooks`, `review`, `fix`, and `finalize`, and `sympohy` keeps them
exclusive per issue.

The watcher runs as a foreground daemon. Under systemd, the user service keeps
it alive while the watcher polls open issues on the configured interval,
selects issues that do not already have a `sympohy` status label, and fills
available worker slots up to the configured maximum. Each worker creates an
issue branch in an independent worktree.

Workers use the normal local Codex CLI environment, including `HOME`,
`CODEX_HOME`, repository rules, and repository skills. `codex exec` must not be
run with flags that ignore user config or repo rules.

## Rejected Alternatives

- Keep the prior runner and add an outer scheduler: parallel worktree
  management, label state, Codex command policy, PR merge gates, and run log
  retention are now core requirements. Splitting them across two tools would
  obscure ownership.
- Move the runner into the application package: this would mix development
  operations with the SIFTQ product runtime and increase frontend dependency
  surface without serving the application.
- Run from GitHub-hosted Actions: the intended environment depends on the local
  Codex CLI session, repository-local rules and skills, authenticated `gh`, and
  the systemd user service.

## Consequences

- `sympohy` can evolve with the repository workflow and tests without waiting on
  an external package.
- Local operators must keep `gh`, `git`, `task`, and Codex CLI authenticated and
  available.
- Systemd installation writes user units outside the repository, while the
  source templates remain versioned under `.sympohy/systemd`.
- Blocked runs intentionally retain worktrees and logs so a human can inspect
  and recover the run.
