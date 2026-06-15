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

## Workflow Semantic Mapping

This step maps the old TAKT task concepts to the current `sympohy` execution
model. There is no active `.takt/` task store in this worktree, so this mapping
is a semantic compatibility record rather than a data migration script.

### Task Data

Current issue state is represented by one status label from `sympohy:pending`,
`sympohy:running`, `sympohy:blocked`, or `sympohy:done`, plus at most one
`sympohy:phase:*` label.

| Legacy TAKT / taqt concept | Current `sympohy` owner | Mapping |
| --- | --- | --- |
| Queued GitHub Issue task from `takt add` | GitHub Issue plus `sympohy:*` labels | Open issues without a `sympohy` status label are fresh candidates. |
| `ai:impl-ready` readiness label | AC/DoD extraction during triage | `sympohy refine` and `sympohy run` require the latest complete AC/DoD set from the issue body or comments; missing readiness becomes `sympohy:blocked` in `triage`. |
| TAKT workflow step name | `sympohy:phase:*` label and `state.json.phase` | `refine_issue`, `plan`, and readiness checks map to `triage`; `implement` maps to `implement`; validation maps to `hooks`; adversarial review maps to `review` and `fix`; PR handoff and merge map to `merge`. |
| TAKT `COMPLETE` | `sympohy:done` plus closed issue | Successful merge marks the issue done, closes it, removes the worktree, and retains run logs. |
| TAKT `ABORT` / blocked result | `sympohy:blocked` | Blocked runs keep the issue worktree and `.sympohy/runs/issue-<number>` logs for inspection. |

### State and Metadata

| Legacy TAKT / taqt concept | Current `sympohy` metadata | Mapping |
| --- | --- | --- |
| `.takt/config.yaml` provider, language, VCS, and branch fields | `.sympohy/config.yaml` plus normal local Codex and GitHub CLI config | `sympohy` is repository-local Python and uses the operator's normal `codex`, `gh`, `git`, and Taskfile environment. |
| TAKT `concurrency: 1` | `max_workers: 10` | Watch mode can start up to ten independent issue workers. |
| TAKT default branch prefix | `worktree_root`, issue branch, and `base_branch` | Each issue uses `.sympohy/worktrees/issue-<number>` on `issue-<number>-sympohy` from `main`. |
| TAKT commit message template | Logical-step commit convention | Implementation recovery counts commits with `#<issue> feat(sympohy): implement logical step <n>`. |
| TAKT queue-local task state | `.sympohy/runs/issue-<number>/state.json` | Run state records `run_id`, issue, status, phase, pid, heartbeat, lock, branch, worktree, plan reference, progress, and recovery metadata. |
| TAKT workflow-local artifacts | `.sympohy/runs/issue-<number>/` | Run logs, `plan.json`, `state.json`, `run.lock`, and `recovery.log` are retained outside application runtime paths. |

### Commands

| Legacy TAKT command | Current command | Mapping |
| --- | --- | --- |
| `task setup:takt` | `task setup:sympohy` | Validates local prerequisites for the repo-local runner. |
| `task ai:takt -- '#<issue>'` | `task ai:sympohy -- '#<issue>'` | Runs a single issue through triage, implementation, hooks, review, PR, and merge handling. |
| `task ai:takt:refine -- '#<issue>'` | `task ai:sympohy:refine -- '#<issue>'` | Checks whether the issue has a complete AC/DoD set and blocks triage when it does not. |
| `task ai:takt:add` and `task ai:takt:run` | `task ai:sympohy:watch` | Queueing is label-driven; the watcher selects fresh or stale open issues and spawns workers. |
| `task ai:takt:doctor` | `task ai:sympohy:doctor` | Validates config, labels, systemd templates, hooks, Codex command shape, and commit subjects. |
| None in TAKT | `task ai:sympohy:resume` | Resumes stale or interrupted `pending` and `running` issues from saved state. |
| None in TAKT | `task ai:sympohy:labels:sync` | Creates or updates `sympohy:*` labels and removes legacy `ai:*` repository labels. |
| None in TAKT | `task ai:sympohy:systemd:install` and `task ai:sympohy:systemd:status` | Installs and inspects the local systemd user timer for watch mode. |

### Automation Hooks

| Legacy TAKT / taqt concept | Current `sympohy` hook | Mapping |
| --- | --- | --- |
| Workflow `rules.next` transitions | Python runner phase transitions | `sympohy` owns transitions in `scripts/sympohy/runner.py` and enforces one active status and one active phase label. |
| TAKT `required_permission_mode` and `edit` flags | Normal Codex user config and repository rules | `codex exec` is invoked without flags that ignore user config or repo rules. |
| TAKT validation instruction to use `task ci` | `.sympohy/config.yaml` `hooks` | The configured final hook is `task ci`, with retry and block behavior on repeated failure. |
| TAKT parallel adversarial review step | Review/fix loop | `sympohy` parses review JSON and repeats fixes while critical, high, or medium findings remain. |
| TAKT final report / PR handoff | Draft PR, final verifier, GitHub checks, squash merge | `sympohy` creates the draft PR, records review output, requires verifier JSON and passing checks, then merges and closes the issue. |
| No stale-run recovery in TAKT | Heartbeat and lock inspection | The watcher reselects stale `pending` or `running` issues when state is missing, pid is dead, heartbeat expires, or lock/state metadata allow takeover. |

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
