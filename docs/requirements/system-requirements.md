---
codd:
  node_id: req:siftq-system
  type: requirement
  status: draft
  depends_on: []
  depended_by:
    - id: design:codd-foundation
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
    - id: design:ci-cd-foundation
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
    - id: design:siftq-project-name-adr
      relation: depends_on
      semantic: governance
    - id: design:sympohy-ticket-driven-ai-runner-adr
      relation: depends_on
      semantic: governance
    - id: req:sympohy-llm-loop-observability-self-improvement
      relation: depends_on
      semantic: governance
    - id: req:sympohy-terminal-resume-review-hardening
      relation: depends_on
      semantic: governance
    - id: design:sympohy-llm-loop-observability-self-improvement
      relation: depends_on
      semantic: governance
    - id: design:sympohy-llm-loop-observability-self-improvement-adr
      relation: depends_on
      semantic: governance
    - id: design:sympohy-terminal-resume-review-hardening
      relation: depends_on
      semantic: governance
    - id: design:contributing-workflow-source-of-truth-adr
      relation: depends_on
      semantic: governance
    - id: design:development-flow
      relation: depends_on
      semantic: governance
    - id: design:contributing-workflow-source-of-truth-adr
      relation: depends_on
      semantic: governance
    - id: design:contributing-workflow-source-of-truth
      relation: depends_on
      semantic: workflow
    - id: design:requirements-template
      relation: depends_on
      semantic: governance
    - id: design:design-template
      relation: depends_on
      semantic: governance
    - id: design:wireframe-template
      relation: depends_on
      semantic: governance
    - id: design:pytest-as-default-python-test-runner-adr
      relation: depends_on
      semantic: governance
    - id: design:taskfile-command-runner
      relation: depends_on
      semantic: governance
    - id: design:design-docs-localization-split
      relation: depends_on
      semantic: governance
    - id: design:design-index
      relation: depends_on
      semantic: governance
    - id: design:codex-configuration-memo
      relation: depends_on
      semantic: governance
    - id: design:rust-tauri-v2-local-application-adr
      relation: depends_on
      semantic: governance
    - id: design:sqlite-tauri-rust-backend-boundary-adr
      relation: depends_on
      semantic: governance
    - id: design:real-sqlite-test-strategy-adr
      relation: depends_on
      semantic: governance
    - id: req:matrix-mvp-v2-browser-storage
      relation: depends_on
      semantic: product
    - id: design:browser-only-matrix-runtime-storage-adr
      relation: depends_on
      semantic: governance
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: product
    - id: req:matrix-mvp-non-functional
      relation: depends_on
      semantic: product
    - id: design:matrix-terminal-drop-hitbox-fix
      relation: depends_on
      semantic: governance
---

# SIFTQ System Requirements

This document is the initial CoDD requirements anchor for the repository.

## Goals

- Keep project requirements, design notes, implementation, and tests traceable.
- Use CoDD checks before merging changes that affect project behavior.
- Record implementation evidence in source files, tests, and reviewed documents.

## Current Scope

- Establish the CoDD configuration baseline.
- Track future functional requirements under `docs/requirements/`.
- Track future design decisions under `docs/design/`.
- Maintain design documentation so it can be localized, split by feature, and
  renamed while preserving CoDD traceability and repository links.
- Track contributor workflow conventions under `docs/contributing/`.

## Acceptance Criteria

- The repository contains a CoDD configuration at `.codd/codd.yaml`.
- Regeneratable CoDD artifacts are excluded from Git.
- Contributors can install project tools with `aqua install`, install project
  dependencies with `task setup`, and run `task codd:version`.
- Design documentation updates keep titles, major headings, body text, CoDD
  front matter, and cross-document links consistent with the current document
  structure.
