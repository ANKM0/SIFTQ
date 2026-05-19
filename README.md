# Yoriwake

Yoriwake is managed with CoDD (Coherence-Driven Development).

## CoDD setup

Install project tools with aqua, then install project dependencies with Task:

```bash
aqua install
task setup
task codd:version
```

The local CoDD configuration lives in `.codd/codd.yaml`. It scans:

- `src/` for implementation files
- `tests/` for verification files
- `docs/` for requirements and design documents
- `aqua.yaml` as project tooling configuration

## Common commands

```bash
task codd:scan
task codd:dag
task codd:elicit
```

Generated graph data and reports are ignored by Git.

## Frontend setup

The v1 Matrix MVP frontend uses pnpm.

```bash
aqua install
task setup:frontend
```

Common frontend checks:

```bash
task ci:typecheck
task ci:lint
task ci:test
task ci:build
```

## CI checks

Run the same local checks before opening or updating a pull request:

```bash
task setup:python
task setup:frontend:ci
task ci
```

## Commit messages

See `docs/contributing/commit-message-format.md`.
