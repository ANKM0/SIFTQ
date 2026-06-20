---
codd:
  node_id: design:design-index
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:design-docs-localization-split
      relation: depends_on
      semantic: index
---

# Design Documents

This directory contains feature-level design documents for SIFTQ. Design files
are named by feature or system capability rather than GitHub issue number so
they remain discoverable after issue-specific work is merged.

## Feature Designs

| Document | CoDD node | Status |
| --- | --- | --- |
| [CI/CD 基盤設計](./ci-cd-foundation.md) | `design:ci-cd-foundation` | Draft |
| [CoDD 基盤設計](./codd-foundation.md) | `design:codd-foundation` | Draft |
| [Matrix MVP 技術選定設計](./matrix-mvp-technology-selection.md) | `design:matrix-mvp-technology-selection` | Implemented |
| [Taskfile コマンドランナー設計](./taskfile-command-runner.md) | `design:taskfile-command-runner` | Draft |
| [sympohy 実行ライフサイクル・状態設計](./sympohy-run-lifecycle-state.md) | `design:sympohy-run-lifecycle-state` | Draft |
| [sympohy 停滞実行復旧設計](./sympohy-stale-run-recovery.md) | `design:sympohy-stale-run-recovery` | Draft |
| [設計書日本語化・機能単位分割設計](./design-docs-localization-split.md) | `design:design-docs-localization-split` | Draft |

## Templates

- [Design template](./templates/design.md)
