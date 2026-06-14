---
codd:
  node_id: design:takt-ticket-driven-ai-runner-adr
  type: design
  status: superseded
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:taskfile-command-runner-adr
      relation: depends_on
      semantic: automation
---

# ADR 0011: TAKT for Ticket-Driven AI Runner

## Status

Superseded by ADR 0013.

## Context

This ADR recorded the previous ticket-driven AI runner decision.

## Decision

The current decision is ADR 0013, which adopts `sympohy` as the repository-local
GitHub Issue runner.

## Rejected Alternatives

- None retained here. The superseding decision owns the active alternatives.

## Consequences

- Historical references should use this ADR only to understand that the prior
  decision has been replaced.
- Active issue execution guidance lives in
  `docs/contributing/issue-execution.md`.
