---
codd:
  node_id: design:issue-73-taqt-takt-inventory
  type: design
  status: draft
  depends_on:
    - id: design:takt-ticket-driven-ai-runner-adr
      relation: depends_on
      semantic: historical-context
    - id: design:sympohy-ticket-driven-ai-runner-adr
      relation: depends_on
      semantic: replacement-decision
    - id: design:sympohy-issue-execution
      relation: depends_on
      semantic: active-workflow
    - id: design:taskfile-command-runner-adr
      relation: depends_on
      semantic: command-entrypoint
---

# Issue 73 taqt/TAKT Inventory

## Scope

This inventory records existing `taqt`, `takt`, `TAKT`, and `.takt` usage before
finishing the issue #73 migration from the legacy TAKT task runner to the
repository-local `sympohy` runner.

The local repository currently uses the spelling `takt` and `TAKT` in historical
references. No local files or directories use the `taqt` spelling.

## Search Result Summary

- `.takt/` directory: absent from this worktree.
- `taqt` references: none found in tracked or visible local files.
- TAKT runtime configuration: none found.
- TAKT Taskfile commands: none found.
- TAKT CI commands: none found.
- TAKT package dependency references: none found in `package.json`,
  `pyproject.toml`, `aqua.yaml`, or lockfile-visible configuration.
- Remaining `takt` and `TAKT` references are historical documentation, ignore
  rules, Markdown-check exclusions, and workflow contract tests that prevent
  reintroducing TAKT commands.

## Active sympohy Surface

The active replacement workflow already exists in these locations:

- `.sympohy/config.yaml`: configures `sympohy` worker limits, issue worktree and
  run-log roots, stale-running threshold, review rounds, retry attempts, and
  the final `task ci` hook.
- `.sympohy/systemd/`: stores user systemd service and timer templates for the
  local watcher.
- `scripts/sympohy/`: contains the repository-local runner CLI, configuration,
  GitHub adapter, core label/review logic, runner, and systemd installer.
- `Taskfile.yml`: exposes `setup:sympohy`, `ai:sympohy`,
  `ai:sympohy:refine`, `ai:sympohy:resume`, `ai:sympohy:doctor`,
  `ai:sympohy:labels:sync`, `ai:sympohy:watch`,
  `ai:sympohy:systemd:install`, and `ai:sympohy:systemd:status`.
- `docs/contributing/issue-execution.md`: documents the active `sympohy`
  workflow and label lifecycle.
- `docs/adr/0013-sympohy-ticket-driven-ai-runner.md`: records the accepted
  replacement decision.
- `tests/sympohy/`: verifies `sympohy` workflow contracts and Python runner
  behavior.

## Remaining TAKT References

| File | Reference type | Inventory note |
| --- | --- | --- |
| `.gitignore` | Legacy local state ignore | Keeps `.takt/` untracked if old generated files exist locally. No `.takt/` directory exists in this worktree. |
| `scripts/ci/check_markdown.py` | Markdown scan exclusion | Excludes `.takt` alongside generated/local directories. This is a defensive exclusion, not active TAKT integration. |
| `docs/adr/0009-taskfile-command-runner.md` | CoDD relationship | Lists the superseded TAKT ADR as a dependent historical decision. |
| `docs/adr/0011-takt-ticket-driven-ai-runner.md` | Historical ADR | Superseded by ADR 0013 and points active guidance to `docs/contributing/issue-execution.md`. |
| `docs/adr/README.md` | ADR index | Lists ADR 0011 as superseded by ADR 0013. |
| `docs/requirements/system-requirements.md` | CoDD relationship | Lists the superseded TAKT ADR under system-governance dependents. |
| `tests/sympohy/sympohyWorkflowContracts.test.ts` | Regression guard | Asserts `Taskfile.yml` does not contain `ai:takt`, `setup:takt`, or `pnpm dlx takt`. |

## Task Workflow Status

The current Taskfile workflow is already `sympohy`-first:

- `task setup` depends on `setup:sympohy`.
- `task ci` runs repository checks and CoDD checks, with no TAKT step.
- `task ai:sympohy ...` and related tasks call
  `uv run python -m scripts.sympohy ...`.
- No `ai:takt`, `setup:takt`, or `pnpm dlx takt` command remains in
  `Taskfile.yml`.

## CI Status

GitHub Actions CI installs aqua-managed tools, installs Python and frontend
dependencies, and runs Taskfile-backed checks. It does not reference TAKT
directly.

The CI path validates the active replacement indirectly through:

- `task ci:test`, which runs Vitest and Python `tests/sympohy` unit tests.
- `task codd:scan`, `task codd:validate`, and `task codd:dag`, which include
  repository documentation and Taskfile configuration in the CoDD graph.

## Migration Implications

Issue #73 no longer needs a broad TAKT command removal pass because active TAKT
commands and configuration are already absent. Later logical steps should decide
whether to keep or remove the defensive `.takt/` ignore and Markdown exclusion.
Historical ADR and CoDD references should remain unless the project decides to
delete superseded-decision history, because they explain why `sympohy` replaced
TAKT.
