---
codd:
  node_id: req:yoriwake-system
  type: requirement
  status: draft
  depends_on: []
  depended_by:
    - id: design:codd-adoption
      relation: depends_on
      semantic: governance
    - id: design:commit-message-format
      relation: depends_on
      semantic: governance
    - id: design:branch-strategy
      relation: depends_on
      semantic: governance
    - id: design:branch-strategy-adr
      relation: depends_on
      semantic: governance
---

# Yoriwake System Requirements

This document is the initial CoDD requirements anchor for the repository.

## Goals

- Keep project requirements, design notes, implementation, and tests traceable.
- Use CoDD checks before merging changes that affect project behavior.
- Record implementation evidence in source files, tests, and reviewed documents.

## Current Scope

- Establish the CoDD configuration baseline.
- Track future functional requirements under `docs/requirements/`.
- Track future design decisions under `docs/design/`.
- Track contributor workflow conventions under `docs/contributing/`.

## Acceptance Criteria

- The repository contains a CoDD configuration at `.codd/codd.yaml`.
- Regeneratable CoDD artifacts are excluded from Git.
- Contributors can install `uv` with `aqua install`, install Python dependencies
  with `uv sync`, and run `uv run codd version --check`.
