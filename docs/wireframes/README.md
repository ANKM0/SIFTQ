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
---

# Matrix MVP Wireframes

This directory contains the low-fidelity Matrix MVP HTML wireframes.

- `index.html`: state map and links to each wireframe state.
- `matrix-mvp.html`: combined single-screen Matrix MVP layout.
- `matrix-empty.html`: empty matrix areas with local `+` creation entry points.
- `matrix-create.html`: task title creation and validation states.
- `matrix-with-cards.html`: title-only task cards with explicit `Edit` actions in matrix areas.
- `matrix-editing.html`: task title edit modal with title input, Save, and Cancel.
- `matrix-dragging.html`: area-local reorder, matrix area move, and terminal drop targets.
- `matrix-terminal-drop.html`: Done / Skipped terminal drop result with hidden terminal tasks.
- `matrix-mvp.css`: shared low-fidelity wireframe styling.
- `task-list-v3.md`: task list / detail / delete / not found contract for Issue #68.
- `task-list.html`: task list page with draggable list cards and status actions.
- `task-list-dragging.html`: task list drag state.
- `task-list-status-menu.html`: task status menu state.
- `task-list-deleted.html`: post-delete task list state with notification.
- `task-detail.html`: task detail edit state.
- `task-delete-confirm.html`: physical delete confirm state.
- `task-not-found.html`: missing task detail state.

The wireframes follow `docs/requirements/matrix-mvp-functional-requirements.md`.
They show four matrix areas in a 2x2 layout, `Skipped` on the left, `Done` on
the right, local `+` creation for each matrix area, title-only task cards,
explicit task title editing from each task card, matrix reorder and move states,
and Done / Skipped drops that remove tasks from the normal matrix display.

The wireframes intentionally do not define Done / Skipped list views, restore
flows, settings, persistence beyond the current browser session, GitHub
integration, CLI behavior, Rust backend commands, Tauri packaging, SQLite
storage, or additional task card fields.

The task list v3 wireframes follow `docs/wireframes/task-list-v3.md`. They show
the matrix / task list navigation links, a vertical draggable list, status
menu, detail editor, delete confirmation, deleted notification, and not found
state.

The HTML wireframe contract is covered by `tests/docs/wireframeContract.test.ts`.
