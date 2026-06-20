---
codd:
  node_id: design:issue-101-design-docs-localization-split
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
---

# Issue 101 設計書日本語化・機能単位分割設計

## External Design（外部設計）

Issue #101では、`docs/design/` 配下の既存設計書を対象に、日本語化対象と
機能単位への分割・リネーム対象を整理する。利用者から観測できる成果物は、
自然な日本語で読める設計書、機能単位のファイル名、整合したCoDD
front matter、既存requirements、ADR、contributing docsからのリンク維持で
ある。

この作業ではアプリケーションUI、wireframe、runtime behaviorは変更しない。
変更対象はMarkdown設計文書と、必要な場合の参照リンク・CoDD依存関係に限る。

## Internal Design（内部設計）

既存設計書の初期棚卸しは次の通り。

| 現在のファイル | 主な扱い | 方針 |
| --- | --- | --- |
| `codd-adoption.md` | CoDD導入設計 | 日本語化し、CoDD基盤設計として維持する。 |
| `issue-6-matrix-mvp-tech-selection.md` | Matrix MVP技術選定 | 機能単位名へリネームし、MVP技術選定設計として維持する。 |
| `issue-10-taskfile.md` | Taskfile導入 | 機能単位名へリネームし、command runner設計として維持する。 |
| `issue-12-ci-cd.md` | CI/CD導入 | 機能単位名へリネームし、CI/CD基盤設計として維持する。 |
| `issue-82-stale-running-inspection.md` | stale running調査 | sympohy stale実行復旧設計として分割・リネームする。 |

分割・リネーム時は、次の順序で作業する。

1. 各設計書の責務を、機能名、外部設計、内部設計、テスト観点、ADR適用、
   未決事項に分けて確認する。
2. 1つの設計書が複数の機能責務を持つ場合は、機能単位のファイルへ分割する。
3. `node_id`は分割後の機能名に合わせ、古いissue番号中心の名前を避ける。
4. `depends_on`と必要な`depended_by`は、分割後の文書責務と既存ADR・requirements
   の関係に合わせて更新する。
5. requirements、ADR、contributing docs、wireframe文書から旧パスを参照して
   いる場合は新パスへ更新する。

## Test Viewpoints（テスト観点）

ドキュメント変更後は、少なくとも次を確認する。

- `task ci:markdown`でMarkdownの基本品質が通ること。
- `task codd:scan`で新しいCoDD front matterが検出されること。
- `task codd:validate`でnode id、依存関係、参照整合性が通ること。
- `task codd:dag`で依存グラフが循環しないこと。
- `rg`で旧ファイル名と旧node idの参照残りを確認し、必要なリンクを更新すること。

## ADR Application（ADR 適用）

新しいADRは作成しない。Issue #101は、既存のCoDD採用、ADR authoring、
開発フロー、既存ADRを前提にした文書整理であり、runtime、storage、toolchain、
repository workflow、architecture boundaryを新しく決定しない。

ADR参照が必要な設計書では、既存ADRの決定を再決定せず、対象機能への適用内容
だけを記録する。

## Artifact Decisions（成果物判断）

- requirements: existing - `docs/requirements/system-requirements.md`
- design: new - `docs/design/issue-101-design-docs-localization-split.md`
- wireframes: not needed - UI契約やHTML wireframeを変更しないため。
- ADR: not needed - 既存の文書・CoDD運用内の整理であり、永続的な新規決定を
  追加しないため。

## Open Questions（未決事項）

- `issue-82-stale-running-inspection.md`を単一の機能設計に留めるか、runner
  lifecycle、resume、stale inspectionの複数設計書へ分割するかは、本文量と
  参照関係を確認して実装時に最終判断する。
- リネーム後に旧パスからの互換リンクを残すかは、参照元の数を確認して判断する。
