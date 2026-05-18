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
