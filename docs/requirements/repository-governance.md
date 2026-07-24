---
codd:
  node_id: req:repository-governance
  type: requirement
  status: draft
  depends_on: []
  depended_by:
  - id: design:zero-base-task-wireframe
    relation: depends_on
    semantic: governance
  - id: design:pytest-as-default-python-test-runner-adr
    relation: depends_on
    semantic: governance
  - id: design:branch-strategy-adr
    relation: depends_on
    semantic: governance
  - id: design:frontend-port-adapter-boundary-adr
    relation: depends_on
    semantic: governance
  - id: design:browser-spa-v1-matrix-mvp-adr
    relation: depends_on
    semantic: governance
  - id: design:rust-tauri-v2-local-application-adr
    relation: depends_on
    semantic: governance
  - id: design:browser-only-matrix-runtime-storage-adr
    relation: depends_on
    semantic: governance
  - id: design:siftq-project-name-adr
    relation: depends_on
    semantic: governance
  - id: design:sqlite-tauri-rust-backend-boundary-adr
    relation: depends_on
    semantic: governance
  - id: design:dnd-kit-matrix-drag-and-drop-adr
    relation: depends_on
    semantic: governance
  - id: design:pnpm-frontend-package-manager-adr
    relation: depends_on
    semantic: governance
  - id: design:real-sqlite-test-strategy-adr
    relation: depends_on
    semantic: governance
  - id: design:react-typescript-vite-matrix-ui-adr
    relation: depends_on
    semantic: governance
  - id: design:contributing-workflow-source-of-truth-adr
    relation: depends_on
    semantic: governance
  - id: design:commit-message-format
    relation: depends_on
    semantic: governance
  - id: design:adr-authoring
    relation: depends_on
    semantic: governance
  - id: design:command-permissions
    relation: depends_on
    semantic: governance
  - id: design:requirements-template
    relation: depends_on
    semantic: governance
  - id: design:wireframe-template
    relation: depends_on
    semantic: governance
  - id: design:task-management-first-draft
    relation: depends_on
    semantic: governance
  - id: design:design-template
    relation: depends_on
    semantic: governance
  - id: req:sympohy-llm-loop-observability-self-improvement
    relation: depends_on
    semantic: governance
  - id: design:sympohy-llm-loop-observability-self-improvement
    relation: depends_on
    semantic: governance
  - id: design:sympohy-llm-loop-observability-self-improvement-adr
    relation: depends_on
    semantic: governance
---

# Repository Governance Requirements

This document anchors active repository governance documents after the zero-base
redesign removed legacy requirements and design documents from the active docs
tree.

## Scope

- Repository workflow, ADR, command permission, and documentation templates
  remain governed by CoDD frontmatter.
- Deleted legacy requirement and design node ids must not be kept as active
  dependencies.
- Active documents that need a governance root should depend on this node.
