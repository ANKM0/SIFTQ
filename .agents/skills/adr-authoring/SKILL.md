---
name: adr-authoring
description: Create or update SIFTQ Architecture Decision Records using the repository ADR template and numbering conventions.
---

# ADR Authoring

## Overview

Use this skill when creating or updating a SIFTQ Architecture Decision Record
(ADR). ADRs live in `docs/adr/` and capture decisions that affect repository
workflow, architecture, governance, or long-lived project conventions.

## Template

Start from:

```text
.agents/templates/adr.md
```

Create ADR files in:

```text
docs/adr/<four-digit-number>-<short-kebab-title>.md
```

Example:

```text
docs/adr/0002-command-permissions.md
```

## Required Flow

1. Inspect existing ADR filenames under `docs/adr/`.
2. Choose the next four-digit ADR number.
3. Copy the ADR template into `docs/adr/<number>-<short-kebab-title>.md`.
4. Replace every placeholder in the template.
5. Set the CoDD node id to:

```text
design:<short-kebab-title>-adr
```

6. Choose a status:
   - `Proposed.` for a draft decision still under review.
   - `Accepted.` for a decision that is already approved.
   - `Superseded by ADR <number>.` when replacing a prior decision.
7. Keep the ADR focused on one decision.
8. Run `task codd:validate` after editing.

## Writing Rules

- Use concrete context instead of generic background.
- State the decision in direct language.
- Document meaningful alternatives only when they affect the decision.
- List consequences as specific benefits, tradeoffs, and follow-up work.
- Do not mix implementation details that belong in a separate design document
  unless they are essential to understanding the decision.

## CoDD Rules

- Keep ADR files under `docs/adr/` so CoDD validates them with the rest of the
  project documentation.
- Use `type: design` for ADRs.
- Keep `depends_on` relationships explicit. Governance decisions usually depend
  on `req:siftq-system` with `semantic: governance`.
- Add `depended_by` only when an existing document already depends on the ADR
  and the reverse link is useful for navigation.
