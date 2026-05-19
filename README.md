# Yoriwake

Yoriwake is managed with CoDD (Coherence-Driven Development).

## CoDD setup

Install project tools with aqua, then install Python dependencies with uv:

```bash
aqua install
uv sync
uv run codd version --check
```

The local CoDD configuration lives in `.codd/codd.yaml`. It scans:

- `src/` for implementation files
- `tests/` for verification files
- `docs/` for requirements and design documents
- `aqua.yaml` as project tooling configuration

## Common commands

```bash
uv run codd scan
uv run codd dag verify
uv run codd elicit
```

Generated graph data and reports are ignored by Git.

## Frontend setup

The v1 Matrix MVP frontend uses pnpm.

```bash
aqua install
pnpm install
```

Common frontend checks:

```bash
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```

## CI checks

Run the same local checks before opening or updating a pull request:

```bash
uv sync --all-groups
pnpm install --frozen-lockfile
uv run python scripts/ci/check_commit_messages.py
uv run python scripts/ci/check_markdown.py
pnpm typecheck
pnpm lint
pnpm test
pnpm build
uv run codd version --check
uv run codd scan
uv run codd validate
uv run codd dag verify
```

## Commit messages

See `docs/contributing/commit-message-format.md`.
