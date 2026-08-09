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

```bash
uv run python scripts/create_adr.py --title "..." --slug "..." --dry-run
```

## Writing Rules

- Keep it concise.
- Use concrete context.
- State the decision directly.
- Include only meaningful rejected options.
- Keep implementation details out unless needed.
