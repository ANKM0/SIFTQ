# Zero-base Task Wireframe

## Target HTML（対象HTML）

- `index.html`: wireframe state map.
- `matrix-page.html`: 4 area matrix page with drag and drop task cards.
- `task-list.html`: task list page.
- `task-detail.html`: task detail page.
- `task-new.html`: new task creation state.
- `task-status-menu.html`: task detail state with status popover open.
- `task-area-menu.html`: task detail state with area popover open.

## UI Contract（UI契約）

- User can switch between matrix page and task list page.
- Matrix page shows areas `1`, `2`, `3`, and `4` as four quadrants divided by
  two arrows.
- Matrix page shows only tasks with status `do`, grouped by area `1`, `2`,
  `3`, or `4`.
- Matrix task cards show title only because status is always `do` on the
  matrix and area is represented by the quadrant.
- User can create a new task from matrix page or task list page.
- Task list page follows a GitHub Issues-like list shape.
- Task list page shows each task with title, area, and status.
- Task detail page shows editable title and description plus metadata for
  status and area.
- Status is changed through an in-place popover without page transition.
- Area is changed through the same popover shape as status.
- Status choices are `do`, `done`, and `skip`.
- Area choices are always `1`, `2`, `3`, and `4`; area is not nullable.
- Changing status to `skip` or `done` does not change the task area.
- User can reorder tasks inside matrix area `1` through `4`.
- Tasks with status `skip` or `done` are not shown on the matrix page.
- Search, back button behavior, loading, and error handling are omitted in this
  wireframe set.

## States（状態）

- Matrix normal: `do` task cards are grouped by area `1`, `2`, `3`, and `4`.
- List normal: all tasks are displayed in a single list.
- Detail normal: one task is edited with title and description and shows
  status and area metadata.
- New task: title and description are entered before creation.
- Status popover: status choices are visible on the same detail surface.
- Area popover: area choices are visible on the same detail surface.
- Dragging: cards are moved directly on `matrix-page.html`.

## Copy and Layout（文言とレイアウト）

- Page navigation uses `Matrix` and `Tasks`.
- Main action uses `New task`.
- Status action uses the current status text and opens an in-place popover.
- Area action uses the current area text and opens an in-place popover.
- Matrix quadrants are identified by area values `1`, `2`, `3`, and `4`, split
  by horizontal and vertical arrows.
- Matrix card body does not repeat the task status.
- List page uses compact rows, not large cards.
- Detail page places title and description as the main content and status/area
  as side metadata.

## Contract Test（契約テスト）

Contract tests are not updated in this scope. Next implementation scope should
replace old wireframe contract tests with checks for:

- HTML links from `index.html`.
- Matrix / list / detail navigation.
- Status and area popover presence, choices, and no page-transition behavior.
- Matrix cards do not render status badges.
- New task state.
- Matrix area-local reorder state.

## Open Questions（未決事項）

- Exact status names may be adjusted by the new requirements.
- Exact route paths are deferred to the external design document.
