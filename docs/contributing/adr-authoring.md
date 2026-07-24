---
codd:
  node_id: design:adr-authoring
  type: design
  status: draft
  depends_on:
  - id: req:repository-governance
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

Use design docs for feature-specific application: per-feature external design,
internal design, test perspectives, and application of existing ADRs. They
record how an existing ADR applies to one feature, plus UI states and operation
flow.

Design docs must not re-decide ADR decisions. If a feature needs a different
durable decision, create a new ADR or update the existing ADR instead of
embedding the decision in the feature design doc.

ADRs should not carry feature-specific implementation details unless they are
essential to the durable decision. Put screen copy, event flows, operation calls,
and individual test cases in the design doc.

## When To Create An ADR

Create or update an ADR when either condition applies:

- The decision affects multiple features, multiple documents, or repository
  workflow.
- Changing the decision later would require migration, schema changes,
  toolchain migration, runtime changes, storage migration, or architecture
  boundary changes.

Common ADR subjects include architecture decisions, major modules, libraries,
tools, runtime, storage, schema, migration, toolchain, governance, and
architecture boundaries.

Before implementation, record one of these in the feature design decision notes:

- Existing ADR used: cite the ADR and how it applies to the feature.
- New ADR needed: create or update an ADR before implementation.
- ADR not needed: record the reason, such as staying within existing module
  boundaries, runtime, storage, toolchain, and workflow decisions.

## Agent Skill

The repository-local Codex skill for this convention is
`.agents/skills/adr-authoring/SKILL.md`.
