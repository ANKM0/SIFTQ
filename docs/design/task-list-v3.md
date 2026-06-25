---
codd:
  node_id: design:task-list-v3
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: req:task-list-v3
      relation: depends_on
      semantic: product
    - id: req:matrix-mvp-v2-browser-storage
      relation: depends_on
      semantic: storage
    - id: design:browser-only-matrix-runtime-storage-adr
      relation: depends_on
      semantic: decision
---

# Task List v3 Design

## External Design（外部設計）

Matrix 画面は既存互換の初期表示として残し、ヘッダーに `タスク一覧` への遷移リンクを持つ。
Task list page は `#/tasks` で開き、縦並びの draggable list card を表示する。Task detail page は
`#/tasks/:taskId` で開き、一覧から遷移して編集できる。

Task list は active / done / skipped の全 task を常に表示し、status フィルタを持たない。各 card は
area ラベルを含む drag handle、title、description、status button、`詳細`、`削除` を持つ。area は
表示専用で、色だけに依存せず handle 内の文字ラベルで識別する。

`description` が空のときは list で `説明なし` を表示する。detail では title、description、area、
status を編集でき、createdAt / updatedAt を読み取り専用で表示する。detail に存在しない taskId を
指定した場合は not found state を表示する。

物理削除は list と detail の両方から実行でき、削除前に task title を含む確認を出す。削除後は
browser storage から消え、Matrix と task list の両画面から消える。削除後は task list に戻り、
`タスクを削除しました` 通知を表示する。通常の list 状態ではこの通知を出さず、deleted state にも
削除済み task の placeholder は表示しない。

## Internal Design（内部設計）

既存の frontend boundary を維持し、以下の責務で実装する。

- `src/contracts/task.ts`: `description`, `createdAt`, `updatedAt`, `listOrder` を含む task contract。
- `src/domain/taskRules.ts`: title / description validation、status 遷移、area 保持、listOrder 採番と正規化、
  not found 判定、削除後遷移ルール。
- `src/ports/taskRepository.ts`: Matrix と task list の両 UI から使う repository port。
- `src/adapters/browserTaskRepository.ts`: browser storage adapter。古い shape を初回読み込み時に補完する。
- `src/ui/*`: Matrix page、task list page、task detail page、confirm dialog、status menu、notification。

Repository では task を読み込んだ時点で旧 shape を新 shape に補完し、`createdAt` / `updatedAt` が無い場合は
互換的に埋める。`createdAt` は不変、`updatedAt` は mutation 時に更新する。`listOrder` は task list 用の
全体順序として保存し、DnD 後は順序を再計算して永続化する。

Task list の status 変更は `areaId` を保持したまま `status` のみを更新する。`status` を active に戻したときは、
保持していた `areaId` の Matrix area に再表示する。Task detail の area 編集は Matrix area 4 種のみを許可し、
status が done / skipped でも area を保持する。

削除は物理削除として扱い、repository から task を除去する。削除後の遷移先は task list に固定する。

## Test Viewpoints（テスト観点）

- repository tests:
  - old shape から new shape への互換補完
  - `createdAt` / `updatedAt` の初期化と更新
  - `listOrder` の作成時採番、DnD 並び替え、保存
  - `status` 変更時に `areaId` が変わらないこと
  - `active` 復帰時に保持 area へ戻ること
  - 物理削除と not found 参照
- UI tests:
  - `#/tasks` の list 表示、全 status 表示、`説明なし`、status menu、detail 遷移、削除確認
  - `#/tasks/:taskId` の detail 編集、readonly timestamps、not found
  - Matrix との相互遷移
  - list からの DnD 並び替えが Matrix 表示へ影響しないこと
  - list と Matrix に `createdAt` / `updatedAt` が表示されないこと
- accessibility tests:
  - list card の見出し、ボタン、通知、confirm 文が意味を持つこと
  - 主要テキストが status 背景色に対して十分なコントラストを保つこと

## ADR Application（ADR 適用）

新しい ADR は作成しない。`ADR 0018` の browser-only runtime / storage 方針を継続し、この feature は
その上で task contract を拡張する。runtime、toolchain、storage backend の選定を変えないため、
durable decision は既存 boundary の範囲に留まる。

## Open Questions（未決事項）

- 将来 `listOrder` を area 単位に分ける必要が出た場合の再設計は、別 issue で扱う。
