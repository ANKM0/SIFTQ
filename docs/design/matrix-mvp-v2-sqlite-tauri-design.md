---
codd:
  node_id: design:matrix-mvp-v2-sqlite-tauri
  type: design
  status: draft
  depends_on:
    - id: req:matrix-mvp-v2-sqlite-tauri
      relation: depends_on
      semantic: product
---

# Matrix MVP v2 SQLite/Tauri Design

## External Design（外部設計）

v2では、React Matrix UI は Tauri desktop app の webview 上で動作する。
起動時に `desktop-app` は app data directory を解決し、その直下の `tasks.sqlite3`
を使って storage を初期化する。初期化の流れは SQLite open、migration、
health check の順である。

startupに失敗してもアプリ全体は落とさず、UIは storage error を表示する。
ただし browser SPA 単体では storage を代替せず、Tauri runtime required を
表示して起動不可とする。

Tauri command は次を公開する。

- `get_storage_health`
- `create_task`
- `list_tasks`
- `move_task`
- `reorder_task`
- `update_task_title`

`list_tasks` は Done / Skipped を含む全taskを返し、UIは active task のみを
Matrix 上に表示する。mutation後は frontend が `list_tasks` を再取得する。

## Internal Design（内部設計）

workspace は `crates/core` と `src-tauri` を持つ。

- `app-core` は Rust library crate として task domain、application service、
  repository trait、SQLite repository、migration、ID generator を持つ。
- `desktop-app` は Tauri shell と command adapter のみを持ち、SQLite 詳細や
  migration 詳細に直接依存しない。
- 手書き contract は `src/contracts/*` に置き、将来 Rust 型から TypeScript 型
  を生成する方針へ置き換えるための `MEMO` を contract 近辺に残す。
- Tauri DTO は `serde(rename_all = "camelCase")` を使って FE contract と対応
  させる。
- error は command 層で frontend 向け DTO に変換し、`code` と `message` を
 返す。

SQLite schema は `tasks(id TEXT PRIMARY KEY, title TEXT NOT NULL, area_id TEXT NOT NULL,
status TEXT NOT NULL, order_index INTEGER NOT NULL)` を基本とする。`area_id`、
`status`、`order_index`、`title` の制約は DB 側でも検証し、`user_version`
で migration を管理する。

v2 では terminal task も `area_id = done/skipped` として保存する。これは
#63 で `area_id` を matrix area のまま保持する model へ移行する前提である。

`TaskService<R, G>` が application rules を担当し、`TaskRepository` trait を
介して `SqliteTaskRepository` を使う。`order_index` は domain では `u32`、
DB では `i64` とし、read/write 両方向で変換する。create / move / reorder /
update は 1 操作を 1 transaction として扱う。

ID は Rust core 側で UUID を生成し、test では deterministic ID generator を
注入できるようにする。

FE 本番 adapter は `tauriTaskRepository` のみとし、`InMemoryTaskRepository` と
repository props injection は削除する。

## Test Viewpoints（テスト観点）

`app-core` のテストは real SQLite を使う。対象は次の通り。

- create / list / move / reorder / update
- title trim と validation
- order 正規化
- Done / Skipped 遷移と DB 保持
- terminal task を matrix area へ戻せないこと
- Done / Skipped task への title update
- `u32` 境界変換
- migration
- unknown schema version
- 一時 file SQLite の reopen で復元されること

`desktop-app` 側は real `app-core` と一時 SQLite DB を使い、command/handler の
成功失敗と structured error 変換を確認する。

FE は repository injection を使わず、`tauriTaskRepository` と `invoke` fake で
command 経由の振る舞いを確認する。

## ADR Application（ADR 適用）

この design では既存の `ADR 0003` を適用し、Rust と Tauri を backend 方針
として使う。加えて、この issue 用の ADR では backend boundary と contract
同期方針を固定し、将来は Rust 型から TypeScript 型生成へ移行する。

test 方針 ADR では、mock より real SQLite を優先し、repository / migration /
command boundary の誤りを実 DB で捕捉する方針を採る。

## Open Questions（未決事項）

- #63 の terminal task model 変更は v2 では実施しない。
- 現時点では、v2 の contract は手書き維持とし、生成導入は別途移行計画で扱う。
