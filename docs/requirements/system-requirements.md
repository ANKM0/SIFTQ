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
    - id: design:command-permissions
      relation: depends_on
      semantic: governance
    - id: design:adr-authoring
      relation: depends_on
      semantic: governance
    - id: design:adr-index
      relation: depends_on
      semantic: governance
    - id: design:agent-roles
      relation: depends_on
      semantic: governance
    - id: design:issue-execution
      relation: depends_on
      semantic: governance
    - id: design:issue-12-ci-cd
      relation: depends_on
      semantic: governance
    - id: design:pnpm-frontend-package-manager-adr
      relation: depends_on
      semantic: governance
    - id: design:github-actions-ci-cd-toolchain-adr
      relation: depends_on
      semantic: governance
    - id: design:taskfile-command-runner-adr
      relation: depends_on
      semantic: governance
    - id: design:issue-10-taskfile
      relation: depends_on
      semantic: governance
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: product
    - id: req:matrix-mvp-non-functional
      relation: depends_on
      semantic: product
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
- Contributors can install project tools with `aqua install`, install project
  dependencies with `task setup`, and run `task codd:version`.
