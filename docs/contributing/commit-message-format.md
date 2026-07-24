---
codd:
  node_id: design:commit-message-format
  type: design
  status: draft
  depends_on:
  - id: req:repository-governance
    relation: depends_on
    semantic: governance
  depended_by:
  - id: design:sympohy-issue-execution
    relation: depends_on
    semantic: workflow
---

# Commit Message Format

## Source of Truth

This document is the canonical source for SIFTQ commit message rules.
Issue #103 keeps the durable rule text here so contributors and
implementation-time agent workflows use the same commit message reference.

SIFTQ commits must include the related GitHub issue number before a
Conventional Commits header.

## Format

```text
#<issue-number> <type>[optional scope][!]: <summary>
```

Examples:

```text
#8 docs: document commit message format
#8 feat(codd): add graph verification command
#8 fix!: rename incompatible config key
```

## Rules

- Start with the GitHub issue number as `#<number>`.
- Add one space between the issue number and the Conventional Commits header.
- Use a Conventional Commits type such as `feat`, `fix`, `docs`, `test`,
  `refactor`, `chore`, `ci`, `build`, `perf`, or `style`.
- Use an optional scope in parentheses when it clarifies the affected area.
- Use `!` before the colon only for breaking changes.
- Write the summary in imperative mood, without a trailing period.

## Body

Use a commit body when the first line is not enough to explain the reason,
tradeoff, migration step, or review context. Keep the first line in the required
format even when a body is present.

## Agent Reference

Implementation-time agents must use this document as the commit message format
reference.
