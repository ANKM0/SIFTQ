---
codd:
  node_id: req:matrix-mvp-v2-browser-storage
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
    - id: design:browser-only-matrix-runtime-storage-adr
      relation: depends_on
      semantic: storage
    - id: design:matrix-mvp-v2-browser-storage
      relation: depends_on
      semantic: product
---

# Matrix MVP v2 Browser Storage Requirements

## 背景

v1のMatrix UIは、ブラウザSPA上でタスク作成、並び替え、area間移動、
Done / Skippedへの遷移を検証できている。v2ではこの操作体験を維持したまま、
ブラウザ単体で使える永続化を追加する。

CLIは追加コンテンツとして後続で扱う。v2ではRust、Tauri、SQLiteを必須にせず、
React / TypeScript / Vite のbrowser appとして、自分のPCのブラウザで利用できる
ことを優先する。

## 概要

この要求仕様は、Issue #59 の更新後v2範囲を定義する。
v2では、React frontendの `TaskRepository` port の背後に browser storage
adapter を置き、task の `id`, `title`, `areaId`, `status`, `order` を保存する。

Issue #68 以降は、この基盤の上で task contract が `description`,
`createdAt`, `updatedAt`, `listOrder` を含むように拡張される。Matrix
用の `areaId` / `order` は引き続き保持され、task list 用の順序は
`listOrder` で別管理する。

保存データは browser storage に格納する。UIはmutation後に全件再取得し、
browser reload 後も同じtask、area、status、orderを復元できる必要がある。

## 機能要件

- `task frontend:dev` で起動したブラウザからMatrix UIを利用できる。
- Tauri runtime や desktop app shell を起動条件にしない。
- browser storage が空の場合は空のMatrixとして起動する。
- browser storage が読めない場合は storage error を表示する。
- task の `id`, `title`, `areaId`, `status`, `order` を browser storage に保存できる。
- task の `description`, `createdAt`, `updatedAt`, `listOrder` を browser storage で扱える。
- `createTask` は matrix area にだけ task を作成できる。
- `listTasks` は Done / Skipped を含む全taskを返す。
- `listTasks` の返却順は area 表示順、次に `order` 昇順で安定している。
- mutation後は frontend が `listTasks` を再取得する。
- task title は trim され、trim後空文字は拒否され、最大256文字に制限される。
- FEの即時validationは `Array.from(title).length` で行う。
- task は areaごとに `order` が `0..n-1` へ正規化される。
- create、move、reorder、title update は1操作ごとに保存される。
- task list の並び順は `listOrder` として保存される。
- Done / Skipped へ移動した task は browser storage に保持され、通常 matrix 表示からは消える。
- Done / Skipped から matrix area へ戻す操作は validation error とする。
- browser reload 後も task title、area、status、order が復元される。

## 非機能要件

- UI、domain rules、storage adapter の責務を分離する。
- dnd-kit 依存は UI interaction layer に閉じる。
- storage adapter は `TaskRepository` port の背後に置く。
- Rust、Tauri、SQLite、native filesystem access は v2 の必須依存にしない。
- ブラウザ上の通常操作で体感速度を損なわないよう、カード移動はReact再描画量とCSS transformを重視する。
- local storage の容量や同期制約を超える要求は後続issueで再評価する。

## 関連Issue

- #59

## 未決事項

- 複数端末同期、公開URL、GitHub連携、CLI、IndexedDB / OPFS への移行は後続issueで扱う。
