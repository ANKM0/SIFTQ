---
codd:
  node_id: req:task-list-v3
  type: requirement
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: product
    - id: req:matrix-mvp-v2-browser-storage
      relation: depends_on
      semantic: storage
  depended_by:
    - id: design:task-list-v3
      relation: depends_on
      semantic: product
---

# Task List v3 Requirements

## 背景

Issue #68 では、既存の Matrix 画面を起点にしたまま、タスクを一覧表示・詳細編集・物理削除できる
`#/tasks` 体験を追加する。Issue #70 では、その task list に checkbox 選択と一括削除を追加し、
既存の単一削除、status 変更、detail 編集、DnD を壊さずに拡張する必要がある。Matrix の既存体験を
壊さず、`description`、`createdAt`、`updatedAt`、`listOrder` を含む task contract に拡張する必要がある。

## 概要

この要求仕様は、Matrix 画面と共存する task list page、task detail page、削除確認、not found、
DnD による listOrder 管理、checkbox 選択、一括削除、browser storage 互換補完を定義する。

Matrix は初期表示として引き続き利用できる。`#/tasks` は縦並びの draggable list card を表示し、
`#/tasks/:taskId` は task の詳細編集を提供する。

## 機能要件

- `#/tasks` で task list page を開ける。
- 初期表示は既存互換として Matrix 画面を表示し、Matrix 画面から task list page へ移動できる。
- Matrix 系 HTML と Tasks 系 HTML のヘッダーには `マトリックス` / `タスク一覧` の相互遷移リンクを表示する。
- `#/tasks/:taskId` で task detail page を開ける。
- task list page は table ではなく、縦並びの draggable list card で表示する。
- task list page は active / done / skipped の全 task を常に表示し、status フィルタを持たない。
- task list page の各 list card には、左端に `area` ラベルを含む drag handle と、task title を含む
  accessible name を持つ checkbox、`title`, `description`, status button, `詳細`, `削除` を表示する。
- checkbox は複数選択でき、選択中の card は task list 上で視認できる。
- task list header には選択件数を表示し、一括削除 button を配置する。
- 選択 task が 0 件の場合、一括削除 button は disabled になる。
- 選択 task が 1 件以上の場合、一括削除 button は enabled になる。
- 一括削除 button を押すと、選択件数を含む確認を表示する。
- 確認でキャンセルした場合、task は削除されず、選択状態も維持される。
- 確認で削除した場合、選択済み task は browser storage から物理削除される。
- 一括削除した task は Matrix / task list / task detail から表示されない。
- 一括削除後、task list 上部に `選択したタスクを削除しました` 通知を表示する。
- 一括削除後、選択状態は空になる。
- 一括削除後、残った task の `listOrder` は `0..n-1` に正規化される。
- 一括削除後、active task の matrix area `order` は表示対象内で `0..n-1` に正規化される。
- status button を押すと、`active`, `done`, `skipped` の選択肢を表示する。
- `description` が空の場合、task list では `説明なし` を表示する。
- Matrix area と task list の area は色分けせず、位置、見出し、area 文字ラベルで識別する。
- task list の各 list card は、status 背景色を使う場合も本文テキストが 4.5:1 以上のコントラストを保ち、
  色だけで status を伝えない。
- task list の `area` は表示のみとし、area 編集は detail で行う。
- `description` は任意入力で、空文字を許可し、list では短く省略表示し、detail では全文を編集できる。
- task contract と browser storage は `description`, `createdAt`, `updatedAt`, `listOrder` を保持する。
- 既存 browser storage の task に新しい field が無い場合は、初回読み込み時に互換的に補完される。
- `createdAt` は task 作成時に設定され、以後変更されない。
- `updatedAt` は task 作成時に `createdAt` と同じ値で設定され、`title`, `description`, `area`, `status`,
  `listOrder` の変更時に更新される。
- `createdAt` / `updatedAt` は Matrix 画面と task list には表示せず、task detail に読み取り専用で表示する。
- task list の初期 `listOrder` は `createdAt` 昇順で採番される。
- 新規 task は task list の末尾に追加される。
- task list は DnD で全 task を手動並び替えでき、DnD 後の順序は `listOrder` として browser storage に保存される。
- task list の DnD は Matrix の `areaId` / `order` に影響しない。
- list から task の `status` を `active` / `done` / `skipped` に変更できる。
- list から `status` を変更しても `areaId` は変更されない。
- `status` を `active` に戻すと、保持していた `areaId` の matrix area に再表示される。
- detail では `title`, `description`, `area`, `status` を編集できる。
- detail の `area` は `Do`, `Schedule`, `Delegate`, `Eliminate` の matrix area 4種から選択する。
- detail の `status` は `active`, `done`, `skipped` から選択する。
- detail で `status !== active` の task も `area` を保持し、`active` に戻すとその area に再表示される。
- list と detail から task を物理削除できる。
- 物理削除前に task title を含む確認を表示する。
- 物理削除後、task は browser storage から削除され、Matrix / list / detail から表示されず、task list へ遷移する。
- 物理削除後の task list 上部には `タスクを削除しました` 通知を表示し、通常の list 状態ではこの通知を表示しない。
- 物理削除後の task list には削除済み task の placeholder や復元操作を表示しない。
- 存在しない task の detail URL を開いた場合は not found 状態を表示し、list へ戻れる。

## 非機能要件

- task list は keyboard 操作や assistive technology からも意味が分かる見出し、ボタン、確認文を持つ。
- checkbox、選択件数、一括削除確認、通知は assistive technology からも意味が分かる文言にする。
- `description` の省略表示は、詳細で全文を確認・編集できることを前提とする。
- `createdAt` / `updatedAt` は UX 上の補助情報として扱い、Matrix と task list では隠す。
- 破壊的な削除は復元 UI を持たず、確認後に確実に反映される必要がある。

## 関連Issue

- #68
- #70

## 未決事項

- 同期や共有、公開 URL、CLI 連携は後続 issue で扱う。
