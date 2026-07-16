---
codd:
  node_id: design:matrix-mvp-wireframe
  type: design
  status: draft
  depends_on:
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: ui
    - id: design:matrix-mvp-wireframe-layout-adr
      relation: depends_on
      semantic: decision
  depended_by:
    - id: design:task-list-v3-wireframe
      relation: depends_on
      semantic: ui
---

# Matrix MVP Wireframes

This directory contains the low-fidelity Matrix MVP HTML wireframes.

- `index.html`: state map and links to each wireframe state.
- `matrix-mvp.html`: combined single-screen Matrix MVP layout.
- `matrix-empty.html`: empty matrix areas with local `+` creation entry points.
- `matrix-create.html`: task title creation and validation states.
- `matrix-with-cards.html`: title-only task cards with explicit `Edit` actions in matrix areas.
- `matrix-editing.html`: task edit modal with title, description, Save, and Cancel.
- `matrix-dragging.html`: area-local reorder, matrix area move, and terminal drop targets.
- `matrix-terminal-drop.html`: Done / Skipped terminal drop result with hidden terminal tasks.
- `task-list-v3.md`: Issue #68 の Task List v3 wireframe contract。
- `task-list.html`: 全taskを表示するdraggable list cardページ。
- `task-list-selection.html`: checkbox 選択と一括削除 enabled 状態。
- `task-bulk-delete-confirm.html`: 一括削除確認ダイアログ。
- `task-list-bulk-deleted.html`: 一括削除後の成功通知付き一覧状態。
- `task-list-deleted.html`: 物理削除後の削除成功通知付き一覧状態。
- `task-list-dragging.html`: list card DnDでlistOrderだけを更新する並び替え状態。
- `task-list-status-menu.html`: status buttonからstatus選択肢を表示する状態。
- `task-detail.html`: task詳細編集formと読み取り専用の作成日時 / 更新日時。
- `task-delete-confirm.html`: 物理削除前の確認状態。
- `task-not-found.html`: 存在しないtask詳細URLの404状態。
- `matrix-mvp.css`: shared low-fidelity wireframe styling.
- `task-list-v3.md`: task list / detail / delete / not found contract for Issue #68.
- `task-list.html`: task list page with draggable list cards and status actions.
- `task-list-selection.html`: task list selected state with bulk delete enabled.
- `task-bulk-delete-confirm.html`: bulk delete confirmation state.
- `task-list-bulk-deleted.html`: bulk delete success state.
- `task-list-dragging.html`: task list drag state.
- `task-list-status-menu.html`: task status menu state.
- `task-list-deleted.html`: post-delete task list state with notification.
- `task-detail.html`: task detail edit state.
- `task-delete-confirm.html`: physical delete confirm state.
- `task-not-found.html`: missing task detail state.

The wireframes follow `docs/requirements/matrix-mvp-functional-requirements.md`.
They show four matrix areas in a 2x2 layout, `Skipped` on the left, `Done` on
the right, local `+` creation for each matrix area, title-only task cards,
explicit task title / description editing from each task card, matrix reorder
and move states, and Done / Skipped drops that remove tasks from the normal
matrix display.

The Matrix MVP wireframes intentionally do not define Done / Skipped list
views, restore flows, settings, persistence beyond the current browser session,
GitHub integration, CLI behavior, Rust backend commands, Tauri packaging,
SQLite storage, or additional Matrix task card fields.

Task List v3 wireframes は Issue #68 の UI contract を追加するが、Matrix card
表示は変更しない。Matrix card は引き続き title-only とし、Matrix edit modal
では title / description を編集する。task list は title, description, area,
status, 詳細, 削除を表示する draggable list card を使い、Issue #70 では checkbox
選択と一括削除の状態を追加する。task詳細は作成日時 / 更新日時をreadonly metadataとして表示し、
Matrix と task list にはそれらの日時を表示しない。

The task list v3 wireframes follow `docs/wireframes/task-list-v3.md`. They show
the matrix / task list navigation links, a vertical draggable list, selection
state, bulk delete confirmation, bulk delete notification, status menu, detail
editor, delete confirmation, deleted notification, and not found state.

The HTML wireframe contract is covered by `tests/docs/wireframeContract.test.ts`.
