---
name: feature-docs-planning
description: Decide which SIFTQ feature documentation artifacts are required, reusable, or unnecessary before implementation. Use when planning or reviewing requirements, design, wireframes, ADR needs, or development-flow stage gates for a feature or issue.
---

# Feature Docs Planning

## Overview

Use this skill to decide and record the documentation artifacts for a feature
before implementation. Follow `docs/contributing/development-flow.md`; the
development-flow diagram is the source of truth for stage gates.

## Decision Rule

For each artifact type, do not check only whether a new file exists. Record one
of these outcomes:

- `new`: create the artifact from the relevant template.
- `existing`: cite and, if needed, update an existing artifact.
- `not needed`: record the reason the artifact is unnecessary.

Block or ask for manual confirmation when none of those outcomes is recorded.

## Artifact Decisions

### Requirements

Use `docs/requirements/templates/requirements.md` when creating a new
requirements document.
Use an existing requirements document when it already covers the requested
feature. Record `not needed` only for changes that do not alter product
requirements, AC/DoD, behavior, or scope.

### Design

Use `docs/design/templates/design.md` when creating a new design document. Use
an existing design document when the implementation is an extension of an
already documented design. Record `not needed` only for changes that do not
require external design, internal design, or test viewpoint decisions.

### Wireframes

Use `docs/wireframes/templates/wireframe.md` when a UI change needs a new
wireframe contract. Use existing wireframes when they already cover the UI
state or need small updates. Record `not needed` only when the change has no
user-visible UI contract impact.

### ADR

Create or update an ADR only for durable decisions. Use `.agents/skills/adr-authoring`
for ADR authoring details. Record `not needed` when the feature stays within
existing module boundaries, runtime, storage, toolchain, architecture, and
repository workflow decisions.

## Durable Decision Heuristics

An ADR is usually required when a decision affects multiple features, multiple
documents, repository workflow, architecture boundaries, schema, migration,
runtime, storage, toolchain, governance, or a major library/module choice.

Do not put durable decisions in a feature design doc. If the design requires a
different durable decision from an existing ADR, create a new ADR or update the
existing ADR first.

## Output Format

When asked to decide artifacts, return a concise checklist:

```text
requirements: new | existing | not needed - <path or reason>
design: new | existing | not needed - <path or reason>
wireframes: new | existing | not needed - <path or reason>
ADR: new | existing | not needed - <path or reason>
blockers: <none or manual-confirmation reason>
```
