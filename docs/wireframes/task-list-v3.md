---
codd:
  node_id: design:task-list-v3-wireframe
  type: design
  status: draft
  depends_on:
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: ui
    - id: design:matrix-mvp-wireframe
      relation: depends_on
      semantic: ui
---

# Task List v3 Wireframe

## Target HTML（対象HTML）

- `task-list.html`: 全taskをdraggable list cardとして表示する通常状態。
- `task-list-deleted.html`: 物理削除後の削除成功通知付き一覧状態。
- `task-list-dragging.html`: 一覧cardのDnD並び替え状態。
- `task-list-status-menu.html`: status button押下後のstatus選択状態。
- `task-detail.html`: 詳細編集、area/status編集、読み取り専用日時表示。
- `task-delete-confirm.html`: 物理削除前の確認状態。
- `task-not-found.html`: 存在しないtask詳細URLのnot found状態。

## UI Contract（UI契約）

- Matrix画面から `Tasks` navigationでタスク一覧へ移動できる。
- タスク一覧はtableではなく、縦並びのdraggable list cardで表示する。
- タスク一覧は active / done / skipped の全taskを常に表示し、status filterを持たない。
- 各list cardは左端のdrag handle内にareaを表示し、title, description, status,
  詳細, 削除を持つ。
- statusはcard右側のpill型buttonで表示し、変更可能であることを示す。
- status button押下後は active / done / skipped の選択肢を表示する。
- descriptionが空の場合は `説明なし` を表示する。
- Matrix areaとtask list areaは色分けせず、位置、見出し、area文字ラベルで識別する。
- 各list cardの背景色はstatusに合わせ、activeは白、doneは薄い緑、skippedは
  グレーで表示する。本文テキストは背景に対して4.5:1以上のコントラストを保ち、
  色だけでstatusを伝えない。
- 一覧card内のstatus buttonから `active`, `done`, `skipped` を変更できる。
- 一覧card内のareaは表示のみで、area編集は詳細画面で行う。
- 一覧cardには `createdAt` / `updatedAt` を表示しない。
- 一覧DnDは全taskを対象にし、`listOrder` を更新する。Matrixの `areaId` / `order` には影響しない。
- 詳細では `title`, `description`, `area`, `status` を編集できる。
- 詳細では `createdAt` / `updatedAt` を読み取り専用で表示する。
- 削除前にはtask titleを含む確認を表示する。
- 削除成功後は一覧へ戻る。
- 削除成功後は一覧上部に `タスクを削除しました` 通知を表示し、復元操作は提供しない。
- not found状態は存在しないtask詳細URLを開いた404状態として扱い、一覧へ戻る導線を表示する。

## States（状態）

- 通常一覧: 全task cardが `listOrder` 順で縦に並ぶ。
- 削除後一覧: 削除成功通知を表示し、削除済みtaskを一覧に表示しない。
- DnD中: drag中card、drop位置、保存対象が一覧順であることを示す。
- 詳細: 編集form、保存、削除、タスク一覧へ戻る、readonly timestamps。
- 削除確認: irreversible delete confirmation。削除後は一覧へ戻る。
- Not found: task詳細URLの対象taskが存在しない404状態と一覧への戻り。

## Copy and Layout（文言とレイアウト）

- Header navigationは `マトリックス` と `タスク一覧` を並べ、現在地をactive表示にする。
- List cardの主情報はtitleとdescription、補助情報は左端のarea handleとstatusに分ける。
- 詳細画面では `作成日時` / `更新日時` をform下部のreadonly metaとして表示する。
- Matrix wireframeのtask cardは引き続きtitle-onlyとし、descriptionやtimestampsを表示しない。

## Contract Test（契約テスト）

- `tests/docs/wireframeContract.test.ts` でtask list v3のHTMLリンク、list card形式、
  status filter非採用、detail timestamps、delete confirmation、not foundを固定する。

## Open Questions（未決事項）

- 実装時のDnD library reuseは既存Matrixと同じ `@dnd-kit/core` を優先する。
