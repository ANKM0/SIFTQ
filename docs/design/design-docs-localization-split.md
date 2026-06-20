---
codd:
  node_id: design:design-docs-localization-split
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
  depended_by:
    - id: design:design-index
      relation: depends_on
      semantic: index
---

# 設計書日本語化・機能単位分割設計

## 外部設計

この変更では、`docs/design/` 配下の既存設計書を対象に、日本語化対象と
機能単位への分割・リネーム対象を整理する。利用者から観測できる成果物は、
自然な日本語で読める設計書、機能単位のファイル名、整合したCoDD
front matter、既存requirements、ADR、contributing docsからのリンク維持で
ある。

この作業ではアプリケーションUI、wireframe、runtime behaviorは変更しない。
変更対象はMarkdown設計文書と、必要な場合の参照リンク・CoDD依存関係に限る。

## 内部設計

既存設計書の整理結果は次の通り。

| 新ファイル | 主な扱い |
| --- | --- |
| `codd-foundation.md` | CoDD基盤設計として日本語化する。 |
| `matrix-mvp-technology-selection.md` | Matrix MVP技術選定設計として日本語化・リネームする。 |
| `taskfile-command-runner.md` | Taskfile command runner設計として日本語化・リネームする。 |
| `ci-cd-foundation.md` | CI/CD基盤設計として日本語化・リネームする。 |
| `sympohy-run-lifecycle-state.md` / `sympohy-stale-run-recovery.md` | sympohy実行ライフサイクルと停滞実行復旧へ分割し、日本語化する。 |

分割・リネームでは、各設計書の責務を機能単位で確認し、1つの設計書が複数の
責務を持つ場合は機能単位のファイルへ分割する。`node_id`は分割後の機能名に
合わせ、古いissue番号中心の名前を避ける。`depends_on`と必要な`depended_by`は、
分割後の文書責務と既存ADR・requirementsの関係に合わせて更新する。

## テスト観点

ドキュメント変更後は、少なくとも次を確認する。

- `task ci:markdown`でMarkdownの基本品質が通ること。
- `task codd:scan`で新しいCoDD front matterが検出されること。
- `task codd:validate`でnode id、依存関係、参照整合性が通ること。
- `task codd:dag`で依存グラフが循環しないこと。
- `rg`で旧ファイル名と旧node idの参照残りを確認し、必要なリンクを更新すること。

## ADR適用

新しいADRは作成しない。この変更は、既存のCoDD採用、ADR authoring、
開発フロー、既存ADRを前提にした文書整理であり、runtime、storage、toolchain、
repository workflow、architecture boundaryを新しく決定しない。

ADR参照が必要な設計書では、既存ADRの決定を再決定せず、対象機能への適用内容
だけを記録する。

## 成果物判断

- requirements: existing - `docs/requirements/system-requirements.md`
- design: new - `docs/design/design-docs-localization-split.md`
- wireframes: not needed - UI契約やHTML wireframeを変更しないため。
- ADR: not needed - 既存の文書・CoDD運用内の整理であり、永続的な新規決定を
  追加しないため。

## 未決事項

- 旧パスからの互換リンクは残さない。repository内のCoDD参照は新しいnode idへ
  更新し、Gitのrename履歴で追跡する。
