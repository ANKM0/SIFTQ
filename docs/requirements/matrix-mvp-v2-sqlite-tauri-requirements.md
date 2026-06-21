---
codd:
  node_id: req:matrix-mvp-v2-sqlite-tauri
  type: requirement
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: product
    - id: req:matrix-mvp-non-functional
      relation: depends_on
      semantic: quality
  depended_by:
    - id: design:matrix-mvp-v2-sqlite-tauri
      relation: depends_on
      semantic: product
---

# Matrix MVP v2 SQLite/Tauri Requirements

## 背景

v1のMatrix UIは、ブラウザSPA上でタスク作成、並び替え、area間移動、
Done / Skippedへの遷移を検証できている。v2ではこの操作体験を維持したまま、
保存先をSQLiteへ移し、React frontendをTauri runtime上で動かす。

この段階では、browser-onlyの実行だけでは不十分である。デスクトップアプリ
としての起動、アプリデータディレクトリの解決、永続化、起動時migration、
構造化エラー表示が必要になる。

## 概要

この要求仕様は、Issue #59 のv2範囲を定義する。
v2では、`app-core` Rust library crateがタスクの業務ルールとSQLite accessを
担い、`desktop-app` Tauri appがUI起動とcommand adapterを担う。

保存データは `tasks.sqlite3` に格納し、起動時にmigrationを実行する。
UIはmutation後に全件再取得し、WebView reload / app restart 後も同じtask、
area、status、orderを復元できる必要がある。

v3以降の変更点として、terminal taskの `area_id` を matrix areaのまま保持し、
`status` だけを `done` / `skipped` に変える移行は #63 へ送る。

## 機能要件

- `desktop-app` は Tauri runtime 上で起動できる。
- browser SPA 単体起動では、in-memory fallback ではなく runtime required を表示する。
- startup時に app data directory を解決し、その直下の `tasks.sqlite3` を利用する。
- startup時に SQLite open と migration を実行する。
- storage初期化失敗時でもアプリは起動し、UIに storage error を表示する。
- `get_storage_health` command は成功時に `{ ok: true }` 相当を返す。
- `get_storage_health` command は失敗時に `{ ok: false, code, message }` 相当を返す。
- `get_storage_health` は DB path を返さない。
- `create_task`, `list_tasks`, `move_task`, `reorder_task`, `update_task_title` command を提供する。
- task の `id`, `title`, `areaId`, `status`, `order` を SQLite に保存できる。
- `create_task` は matrix area にだけ task を作成できる。
- `list_tasks` は Done / Skipped を含む全taskを返す。
- `list_tasks` の返却順は area 表示順、次に `order_index` 昇順で安定している。
- mutation後は frontend が `list_tasks` を再取得する。
- task title は trim され、trim後空文字は拒否され、最大256文字に制限される。
- FEの即時validationは `Array.from(title).length` で行う。
- task は areaごとに `order_index` が `0..n-1` へ正規化される。
- create、move、reorder、title update は操作単位で atomic に保存される。
- Done / Skipped へ移動した task は DB に保持され、通常 matrix 表示からは消える。
- Done / Skipped から matrix area へ戻す操作は validation error とする。

## 非機能要件

- SQLite access は `app-core` に閉じ、`desktop-app` は SQLite 実装詳細へ直接依存しない。
- Rust runtime は `rusqlite` を使う。
- migration は `PRAGMA user_version` で管理する。
- `user_version = 0` のDBに初期 schema migration を適用できる。
- `user_version = 1` のDBを正常に開ける。
- unknown schema version は `MIGRATION` error になる。
- Tauri command error は `code` / `message` を持つ構造化DTOで返す。
- startup、storage init、migration failure には最小限の logging を行う。

## 関連Issue

- #59
- #63

## 未決事項

- v3で terminal task の `area_id` を保持する移行は、#63 の design で確定する。
