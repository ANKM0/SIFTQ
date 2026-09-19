---
name: adr-authoring
description: Create or update SIFTQ Architecture Decision Records using the repository ADR template and numbering conventions.
---

# ADR Authoring

Use this skill when creating or updating a SIFTQ ADR.

## Flow

1. Read `docs/contributing/adr.md`.
2. Decide title, slug, and one decision.
3. Draft purpose, background, constraints, decision, rejected options, impact.
4. Use `scripts/create_adr.py` for number, path, and template copy.
5. Update `docs/adr/README.md`.
6. Run the `adr-review` skill on the new or changed ADR and resolve its findings. For new ADRs, run `task -t .config/Taskfile.yml ci:adr` for the deterministic check.

```bash
uv run python scripts/create_adr.py --title "..." --slug "..." --dry-run
```

## Writing Rules

- One ADR records one responsibility. Do not combine multiple responsibilities in one ADR.
- If decisions belong to different responsibilities, split them into separate ADRs.
- Keep it concise.
- Use concrete context.
- State the decision directly.
- Include only meaningful rejected options.
- Keep implementation details out. Do not write identifiers, configuration values, processing order, code, commands, or source paths; leave them to code or design docs.
- To change an accepted ADR, do not rewrite its body. Add `> Status: Superseded by [ADR XXXX](...).` and record the new decision in a new ADR.
