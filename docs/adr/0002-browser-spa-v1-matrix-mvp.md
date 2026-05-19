---
codd:
  node_id: design:browser-spa-v1-matrix-mvp-adr
  type: design
  status: draft
  depends_on:
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: scope
    - id: req:matrix-mvp-non-functional
      relation: depends_on
      semantic: scope
  depended_by:
    - id: design:issue-6-matrix-mvp-tech-selection
      relation: depends_on
      semantic: decision
---

# ADR 0002: Browser SPA for v1 Matrix MVP

## Status

Accepted.

## Context

Yoriwakeの長期的な方向性には、GUIとCLIのインターフェース、DB-backed
storage、GitHub integrationを持つローカルアプリケーションが含まれる。
一方でv1 MVPの目的はより小さく、タスクを作成し、表示し、象限間を
ドラッグアンドドロップで移動できる2次元マトリックスページを検証する
ことである。

v1 MVPを最初から完全なローカルアプリケーションとして始めると、
マトリックス操作が検証される前に、Tauri packaging、Rust command bindings、
persistence、sync concernsを導入することになる。

## Decision

v1 matrix MVPはブラウザSPAとして構築する。これはマトリックス操作の
UI検証マイルストーンとして扱い、最終的なアプリケーション形態とは
みなさない。

v1 MVPには、Tauri、Rust backend commands、SQLite、CLI support、GitHub
integrationを含めない。

## Consequences

- 最小限のinfrastructureでマトリックスUIを構築し、評価できる。
- タスク作成、カード表示、象限間drag and dropに集中できる。
- ローカルアプリケーションの懸念は、UI conceptの検証後まで延期する。
- SPAは、後からUIをTauriへ移せるようにmigration boundaryを明確に保つ
  必要がある。
