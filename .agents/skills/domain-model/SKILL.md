---
name: domain-model
description: Change the SIFTQ domain and data model. Use when adding or changing entities, attributes, domains, transitions, flows, screens, or invariants, or when regenerating and verifying the domain diagrams.
---

# Domain Model

ドメイン / データモデルの変更手順。技術・設計方針は ADR、ドメインの決定と不変条件は `domain.md` が正本。手で編集するのは `presentation.json`（表現・業務フロー）と `api-meta.json`（api のエラー）。`domain-model.json` は `presentation.json` とコードから抽出した `graph.auto.json` をマージした生成物で、手編集しない。

## Flow

### 1. ドメインモデリング

- 手書きの `domain-model.d2` を先に変更する（集約 / 値オブジェクト / 不変条件 / ライフサイクル）。
- `domain.md` / ADR に反映する。why を残す決定は `DEC-TM-xxx`、守るべき性質は `INV-TM-xxx`、横断・構造の決定は ADR。
- `flows` / `screens` / `navigation` の元になる業務・UI 設計をここで決める。

### 2. JSON（論理データモデル）

- `domain-model.schema.json` を先に更新する（探索中は `additionalProperties` を緩めてよい）。
- `presentation.json` を更新する（`domains` / `entities` / `relations` / `flows` / `screens` / `navigation`）。
- `api` はコードのルートから自動抽出する。`api-meta.json` にエラーなどコードから導けない情報を置く。抽出器は `scripts/domain-model/extract.ts`。
- `task docs:domain:svg` で同期・検証 → `logical` / `physical` / `flow` / `nav` / `api` / `api-graph` を生成し、`task docs:domain:viewer` で preview HTML を確認する。`api-graph` は対話的な API グラフ（要 serve）。

### 3. 物理実装

- `migrations/*.sql` を追加・変更する（物理の正本）。
- テストを書き、テスト名に `INV-TM-xxx` を含める。
- `src/task.ts` に不変条件を実装する。
- mapping を必要に応じて更新し、`migrations` と一致することを検証で確認する。

## 完了条件

- `task docs:domain:svg` / `ci:domain` が error 0。warning は未参照 entity のみ許容する。
- `ci:domain` の sync 検査が差分 0（コードとモデルが同期している）。
