---
codd:
  node_id: design:contributing-workflow-source-of-truth-adr
  type: design
  status: draft
  depends_on:
  - id: req:repository-governance
    relation: depends_on
    semantic: governance
  depended_by: []
---

# ADR 0015: Contributing Workflow Source of Truth

## Status

Proposed.

## Context

SIFTQ keeps contributor workflow conventions under `docs/contributing/`.
Issue #103 consolidates branch strategy and commit message format rules so the
contributing docs remain the authoritative references, while repository-local
skills remain available for implementation-time agent workflows.

Duplicating the same branch and commit rules in both contributing docs and
skills creates drift risk. The implementation-time skills still need enough
local instructions to trigger at the right time and guide agents to the right
workflow, but the durable rule text should have one source of truth.

## Decision

Use `docs/contributing/branch-strategy.md` and
`docs/contributing/commit-message-format.md` as the source of truth for SIFTQ
branch and commit rules. Repository-local implementation skills must explicitly
name the contributing docs they read during implementation and should avoid
becoming an independent copy of those rules.

Future changes to branch or commit rules should update the relevant
`docs/contributing/` document first. Skills may then be updated to point to the
same document or to adjust workflow-specific guidance.

## Rejected Alternatives

- Keep full rule copies in both skills and contributing docs. This is rejected
  because small wording changes can make the two sources diverge.
- Make skills the authoritative rule source. This is rejected because
  contributing workflow rules must be reviewable as repository documentation,
  not only as agent-specific instructions.

## Consequences

- Contributors and agents share the same durable rule references.
- Skill validation can focus on trigger metadata, implementation workflow, and
  explicit doc references.
- Rule changes require a contributing doc update before skill wording changes.
- Existing skill users still have a local entry point for branch and commit
  work, but those skills must defer durable rule details to contributing docs.
