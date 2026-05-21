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
---

# TAKT AI Workflow

SIFTQ uses TAKT as the initial ticket-driven AI development runner. TAKT is
development workflow tooling and is not part of the application runtime.

## Tool Management

TAKT is distributed as an npm package. SIFTQ does not add it to `package.json`.
Instead, Taskfile runs the pinned TAKT version through aqua-managed `pnpm`:

```bash
task ai:takt -- --version
```

Warm the package cache when setting up an environment:

```bash
task setup:takt
```

## Single-Issue Flow

Queue a GitHub Issue:

```bash
task ai:takt:add -- '#46'
```

Run queued TAKT tasks:

```bash
task ai:takt:run
```

Validate the project workflow definition:

```bash
task ai:takt:doctor
```

## Workflow Expectations

- Use `.takt/workflows/siftq.yaml` for SIFTQ issue implementation.
- Treat `task ci` as the normal completion gate.
- Include `task codd:validate` evidence for documentation and governance work.
- Follow branch and commit rules from `docs/contributing/`.
- Leave unrelated files and untracked user work untouched.
- Keep TAKT and future schedulers outside SIFTQ runtime dependencies.

## Parallel Execution

Initial operation uses `concurrency: 1`. If multiple issue execution becomes
necessary, add an external scheduler that assigns labels, creates one
`git worktree` per issue, and runs TAKT inside each worktree. Do not make the
first TAKT adoption responsible for long-running multi-worker orchestration.
