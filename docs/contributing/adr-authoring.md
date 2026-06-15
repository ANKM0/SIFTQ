---
codd:
  node_id: design:adr-authoring
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
  depended_by:
    - id: design:adr-index
      relation: depends_on
      semantic: index
---

# ADR Authoring

SIFTQ records long-lived workflow, governance, and architecture decisions as
Architecture Decision Records (ADRs) under `docs/adr/`.

## File Names

Use this format:

```text
docs/adr/<four-digit-number>-<short-kebab-title>.md
```

Choose the next four-digit number after inspecting existing ADR files.

## Template

Start from:

```text
.agents/templates/adr.md
```

Replace every placeholder before committing an ADR. The CoDD node id should use
this format:

```text
design:<short-kebab-title>-adr
```

## Required Sections

- `Status`: the decision state, such as `Proposed.`, `Accepted.`, or
  `Superseded by ADR <number>.`
- `Context`: the background, constraints, and forces that make the decision
  necessary.
- `Decision`: the chosen approach and the main reason for choosing it.
- `Consequences`: the benefits, tradeoffs, operational impact, and follow-up
  work.

## Boundary With Design Docs

Use ADRs for durable decisions, such as architecture decisions, major modules,
libraries, tools, runtime, storage, schema, migration, toolchain, governance,
and architecture boundaries. ADRs record the reasons for those choices.

Use design docs for feature-specific application: how an existing ADR applies to
one feature, the external design, internal design, UI states, operation flow, and
test viewpoints.

Design docs should not re-decide ADRs. If a feature needs a different durable
decision, create a new ADR or update the existing ADR instead of embedding the
decision in the feature design doc.

ADRs should not carry feature-specific implementation details unless they are
essential to the durable decision. Put screen copy, event flows, operation calls,
and individual test cases in the design doc.

## Agent Skill

The repository-local Codex skill for this convention is
`.agents/skills/adr-authoring/SKILL.md`.
