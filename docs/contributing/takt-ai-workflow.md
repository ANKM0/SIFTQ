---
codd:
  node_id: design:takt-ai-workflow
  type: design
  status: draft
  depends_on:
    - id: design:takt-ticket-driven-ai-runner-adr
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
---

# TAKT AI Workflow

SIFTQ uses TAKT as the initial ticket-driven AI development runner. TAKT is
development workflow tooling and is not part of the application runtime.

TAKT supersedes the previous role-based agent workflow and `agent:*`
label-driven gates. The canonical initial workflow is manual execution from a
trusted local environment.

## Tool Management

TAKT is distributed as an npm package. SIFTQ does not add it to `package.json`.
Instead, Taskfile runs the pinned TAKT version through aqua-managed `pnpm`:

```bash
task ai:takt:cli -- --version
```

Warm the package cache when setting up an environment:

```bash
task setup:takt
```

## Single-Issue Flow

Refine a GitHub Issue before implementation:

```bash
task ai:takt:refine -- '#46'
```

Run a GitHub Issue through the TAKT implementation pipeline:

```bash
task ai:takt -- '#46'
```

The implementation entrypoint uses TAKT pipeline mode so the configured
`pipeline.commit_message_template` is applied. Do not route implementation work
through `takt add` followed by `takt run`; TAKT 0.42.0's queued-task
auto-commit path emits `takt: ...` commit subjects, which do not satisfy the
SIFTQ commit message format.

Validate the project workflow definition:

```bash
task ai:takt:doctor
```

## GitHub Labels and Actions

Use `ai:impl-ready` to mark a GitHub Issue whose AC, DoD, ADR need, and design
prerequisites are clear enough for implementation. The implementation workflow
checks this label before planning and reports Blocked when the label is missing
or the AC/DoD/design prerequisite state is unclear.

Do not add a GitHub Actions workflow that starts TAKT from an issue label.
The initial setup assumes Codex subscription/local session execution, which a
GitHub-hosted runner cannot safely reproduce. A label-triggered runner requires
a separately designed self-hosted runner or API-key based execution model and
is out of scope for the initial TAKT adoption.

Labels can still be used by humans for triage, but labels are not the execution
trigger for TAKT in this repository.

## Workflow Expectations

- Use `.takt/workflows/issue-refinement.yaml` when a GitHub Issue needs AC/DoD
  validation, ADR screening, issue updates, or implementation-readiness labeling.
- Use `.takt/workflows/siftq.yaml` for SIFTQ issue implementation.
- Start implementation only after the issue has the `ai:impl-ready` label.
- Treat `task ci` as the normal completion gate.
- Include `task codd:validate` evidence for documentation and governance work.
- Follow branch and commit rules from `docs/contributing/`.
- Leave unrelated files and untracked local work untouched.
- Keep TAKT and future schedulers outside SIFTQ runtime dependencies.

The TAKT workflow contract is covered by
`tests/takt/taktWorkflowContracts.test.ts`.

## Parallel Execution

Initial operation uses `concurrency: 1`. If multiple issue execution becomes
necessary, add an external scheduler that creates one `git worktree` per issue
and runs TAKT inside each worktree. Do not make the first TAKT adoption
responsible for long-running multi-worker orchestration.
