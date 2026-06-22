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
    - id: design:contributing-workflow-source-of-truth
      relation: depends_on
      semantic: index
---

# 設計書一覧

このディレクトリには、SIFTQの機能単位の設計書を配置する。設計書の
ファイル名はGitHub issue番号ではなく、機能名またはシステム能力に基づいて
付ける。これにより、issue単位の作業がmergeされた後も設計意図を見つけ
やすくする。

## 機能設計

| 設計書 | CoDDノード | 状態 |
| --- | --- | --- |
| [CI/CD 基盤設計](./ci-cd-foundation.md) | `design:ci-cd-foundation` | 草案 |
| [CoDD 基盤設計](./codd-foundation.md) | `design:codd-foundation` | 草案 |
| [Contributing Workflow Source of Truth Design](./contributing-workflow-source-of-truth.md) | `design:contributing-workflow-source-of-truth` | 草案 |
| [Matrix MVP 技術選定設計](./matrix-mvp-technology-selection.md) | `design:matrix-mvp-technology-selection` | 実装済み |
| [Matrix MVP v2 SQLite/Tauri Design](./matrix-mvp-v2-sqlite-tauri-design.md) | `design:matrix-mvp-v2-sqlite-tauri` | 草案 |
| [Taskfile コマンドランナー設計](./taskfile-command-runner.md) | `design:taskfile-command-runner` | 草案 |
| [sympohy 実行ライフサイクル・状態設計](./sympohy-run-lifecycle-state.md) | `design:sympohy-run-lifecycle-state` | 草案 |
| [sympohy 停滞実行復旧設計](./sympohy-stale-run-recovery.md) | `design:sympohy-stale-run-recovery` | 草案 |
| [設計書日本語化・機能単位分割設計](./design-docs-localization-split.md) | `design:design-docs-localization-split` | 草案 |

## テンプレート

- [設計書テンプレート](./templates/design.md)
