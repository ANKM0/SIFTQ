---
codd:
  node_id: design:contributing-workflow-source-of-truth
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:contributing-workflow-source-of-truth-adr
      relation: depends_on
      semantic: decision
    - id: design:branch-strategy
      relation: depends_on
      semantic: workflow
    - id: design:commit-message-format
      relation: depends_on
      semantic: workflow
  depended_by:
    - id: design:design-index
      relation: depends_on
      semantic: index
---

# Contributing Workflow Source of Truth Design

## External Design（外部設計）

Issue #103では、branch strategyとcommit message formatの運用ルールを
`docs/contributing/`配下の文書へ集約する。実装後、利用者と実装時agentが
参照する正本は次の文書になる。

- `docs/contributing/branch-strategy.md`
- `docs/contributing/commit-message-format.md`

repository-local skillは、同じルール本文を別管理し続けるのではなく、
実装時に読むcontributing docを明示する。これにより、branch作成、commit
message作成、PR作成時の判断はcontributing docを正本として追跡できる。

Issue #103のAC/DoD確認では、commit message formatとbranch strategyの
専用skillを正本として扱わず、既存のcontributing docsを残すことが
求められている。既存文書の内容確認により、正本は次の2文書とする。

- commit message format: `docs/contributing/commit-message-format.md`
- branch strategy: `docs/contributing/branch-strategy.md`

## Internal Design（内部設計）

実装では次の整理を行う。

- branch strategyの実装時参照は
  `docs/contributing/branch-strategy.md`として明示する。
- commit message formatの実装時参照は
  `docs/contributing/commit-message-format.md`として明示する。
- skillやagent向け補助文書に残す内容は、発火条件、作業手順、
  参照すべき正本文書の案内に限定する。
- branch ruleまたはcommit ruleの本文を変更する場合は、まず
  `docs/contributing/`の正本文書を更新し、skillは必要な参照だけを追従する。

## Test Viewpoints（テスト観点）

- 新しいskill構成が`quick_validate.py`を通過すること。
- `task ci`が通過すること。
- `docs/contributing/branch-strategy.md`と
  `docs/contributing/commit-message-format.md`が存在し、正本として残ること。
- branch strategyとcommit message formatの実装時参照が、それぞれ
  対応するcontributing docを明示していること。
- 実装差分に対するcommit messageが
  `#103 docs: <summary>`形式を満たすこと。

## ADR Application（ADR 適用）

ADR 0015で、contributing workflow rulesの正本を`docs/contributing/`に置き、
repository-local skillはその文書を実装時参照として明示する方針を採用する。
この設計はADR 0015をIssue #103のbranch strategy / commit message format
整理へ適用する。

## Artifact Decisions（成果物判断）

- requirements: existing - `docs/requirements/system-requirements.md`
- design: new - `docs/design/contributing-workflow-source-of-truth.md`
- wireframes: not needed - UI契約やHTML wireframeを変更しないため。
- ADR: new - `docs/adr/0015-contributing-workflow-source-of-truth.md`

## Open Questions（未決事項）

- なし。
