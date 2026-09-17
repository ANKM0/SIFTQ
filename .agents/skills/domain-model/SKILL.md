---
name: domain-model
description: Change the SIFTQ domain and data model. Use when adding or changing entities, attributes, domains, transitions, flows, screens, or invariants, or when regenerating and verifying the domain diagrams.
---

# Domain Model

ドメイン / データモデルの変更手順。技術・設計方針は ADR、ドメインの決定と不変条件は `domain.md` が正本。`domain-model.json` が唯一の編集可能ソースで、生成物は手編集しない。

## Flow

### 1. ドメインモデリング

- 手書きの `domain-model.d2` を先に変更する（集約 / 値オブジェクト / 不変条件 / ライフサイクル）。
- `domain.md` / ADR に反映する。why を残す決定は `DEC-TM-xxx`、守るべき性質は `INV-TM-xxx`、横断・構造の決定は ADR。
- `flows` / `screens` / `navigation` の元になる業務・UI 設計をここで決める。

### 2. JSON（論理データモデル）

- `domain-model.schema.json` を先に更新する（探索中は `additionalProperties` を緩めてよい）。
- `domain-model.json` を更新する（`domains` / `entities` / `relations` / `transitions` / `rules` / `flows` / `screens` / `navigation`）。`db` は持たず論理型は `domains`、論理 → 物理 mapping は生成器のコード。
- `task docs:domain:svg` で検証 → `logical` / `physical` / `flow` / `nav` を生成し、`task docs:domain:viewer` で preview HTML を確認する。

### 3. 物理実装

- `migrations/*.sql` を追加・変更する（物理の正本）。
- テストを書き、テスト名に `INV-TM-xxx` を含める。
- `src/task.ts` に不変条件を実装する。
- mapping を必要に応じて更新し、`migrations` と一致することを検証で確認する。

## 完了条件

- `task docs:domain:svg` / `ci:domain` が error 0。warning は未参照 entity のみ許容する。
