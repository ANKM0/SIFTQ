---
codd:
  node_id: design:design-template
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
---

# <機能名>設計

## 外部設計

ユーザー、テスト、外部モジュールから観測できる振る舞いを記録する。
UI 限定の節ではない。

## 内部設計

実装方針、主要な責務分担、データ構造、依存関係など、外部から直接は
観測されない設計判断を記録する。

## テスト観点

この設計で確認すべき観点、実行するテスト、またはテスト不要と判断した
理由を記録する。

## ADR適用

既存 ADR を参照する場合は、その判断をこの機能へどう適用するかを
記録する。ADR が不要な場合は、不要と判断した理由を記録する。

## 未決事項
