---
codd:
  node_id: design:codex-configuration-memo
  type: design
  status: draft
  depends_on:
  - id: design:command-permissions
    relation: depends_on
    semantic: permissions
  - id: design:sympohy-issue-execution
    relation: depends_on
    semantic: automation
  depended_by: []
---

# Codex Configuration Memo

## Purpose

This memo anchors the repository-local Codex configuration decisions referenced
by the contributing workflow documents.

## Scope

- Codex runs should use the normal user configuration and repository rules.
- Repository command permissions are governed by `.codex/rules/siftq.rules`
  and documented in `docs/contributing/command-permissions.md`.
- `sympohy` automation should pass only role-specific model and reasoning
  settings while preserving the user's `HOME`, `CODEX_HOME`, repository rules,
  and repository skills.

## Non-Goals

- This memo does not define product runtime behavior.
- This memo does not replace ADRs for durable architecture decisions.
