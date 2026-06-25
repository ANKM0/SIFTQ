---
codd:
  node_id: design:task-list-v3-wireframe
  type: design
  status: draft
  depends_on:
    - id: design:task-list-v3
      relation: depends_on
      semantic: ui
  depended_by:
    - id: design:matrix-mvp-wireframe
      relation: depends_on
      semantic: ui
---

# Task List v3 Wireframe

## Target HTML（対象HTML）

- `docs/wireframes/task-list.html`
- `docs/wireframes/task-list-dragging.html`
- `docs/wireframes/task-list-status-menu.html`
- `docs/wireframes/task-list-deleted.html`
- `docs/wireframes/task-detail.html`
- `docs/wireframes/task-delete-confirm.html`
- `docs/wireframes/task-not-found.html`
- `docs/wireframes/index.html`
- `docs/wireframes/README.md`

## UI Contract（UI契約）

- Matrix 画面と task list 画面は相互遷移リンクを持つ。
- task list は縦並びの card list として表示し、table ではない。
- card の左端に area ラベルを含む drag handle があり、area はここでのみ示す。
- card 内には title、description、status button、`詳細`、`削除` がある。
- status button で `active`, `done`, `skipped` のメニューを開く。
- description が空の場合は `説明なし` と表示する。
- detail では title、description、area、status を編集でき、createdAt / updatedAt は readonly。
- 削除確認には task title を含める。
- not found は list へ戻る導線を持つ。

## States（状態）

- `task-list.html`: 通常の task list。全 status の task を表示し、削除通知は出さない。
- `task-list-dragging.html`: drag handle からドラッグ中の状態。並び替え先を視覚化する。
- `task-list-status-menu.html`: status menu を開いた状態。
- `task-list-deleted.html`: 削除後の通知を表示し、削除済み task の placeholder や復元操作を持たない状態。
- `task-detail.html`: 編集フォームと readonly timestamps を含む詳細状態。
- `task-delete-confirm.html`: 物理削除の確認状態。
- `task-not-found.html`: 存在しない taskId の not found 状態。

## Copy and Layout（文言とレイアウト）

- ヘッダーには `マトリックス` / `タスク一覧` の相互遷移リンクを置く。
- list page は `タスク一覧` を大見出しにし、その下に draggable list card を縦に積む。
- `area` は drag handle 内の label のみで示し、色だけで区別しない。
- `description` は 1 行前後で省略し、空なら `説明なし` を出す。
- status menu は `active`, `done`, `skipped` を縦に並べる。
- delete confirm は `"<title>" を削除しますか?` のように title を含める。
- deleted state の上部通知は `タスクを削除しました`。
- timestamps は detail のみで `作成日時` / `更新日時` として表示し、list と Matrix には出さない。

## Contract Test（契約テスト）

- `tests/docs/wireframeContract.test.ts` で task list v3 wireframe contract を固定する。
- `docs/wireframes/task-list-v3.md` に列挙した HTML ファイルの存在と、状態ごとの差分を確認する。
- 既存の Matrix wireframe contract は維持し、task list v3 の追加で壊さない。

## Open Questions（未決事項）

- deleted state の通知を toast 風にするか inline banner にするかは、実装側の UI スタイルで最終決定する。
