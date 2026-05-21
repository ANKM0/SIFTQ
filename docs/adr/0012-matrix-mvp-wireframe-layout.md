---
codd:
  node_id: design:matrix-mvp-wireframe-layout-adr
  type: design
  status: accepted
  depends_on:
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: scope
    - id: design:dnd-kit-matrix-drag-and-drop-adr
      relation: depends_on
      semantic: interaction
  depended_by:
    - id: design:matrix-mvp-wireframe
      relation: depends_on
      semantic: decision
---

# ADR 0012: Matrix MVP Wireframe Layout

## Status

Accepted.

## Context

Matrix MVP needs a low-fidelity wireframe so implementers can confirm the
single-screen area layout, task creation flow, task card display, drag reorder,
area move, and terminal Done / Skipped behavior without adding interpretation
outside the functional requirements.

The functional requirements define six areas for v1: four Eisenhower matrix
areas, `Skipped` as the left-side terminal area, and `Done` as the right-side
terminal area. They also define that Done / Skipped drops update status and
remove tasks from the normal matrix display, while Done / Skipped list views
and restore flows remain out of scope for v1.

## Decision

The Matrix MVP wireframe uses a single screen with `Skipped` on the left, a
2x2 matrix in the center, and `Done` on the right.

The center matrix contains the four matrix areas:

- `Do`: important and urgent.
- `Schedule`: important and not urgent.
- `Delegate`: not important and urgent.
- `Eliminate`: not important and not urgent.

Each matrix area has a `+` creation entry point in its header. Creating a task
from an area adds a card to the bottom of that same area. Task cards display
only the task title.

Dragging within the same matrix area represents area-local reorder. Dragging to
another matrix area represents an active task move. Dropping on `Done` changes
the task status to `done`; dropping on `Skipped` changes the task status to
`skipped`. In both terminal cases, the task disappears from the normal matrix
display instead of being shown as a card inside the terminal area.

For v1, the wireframe explicitly excludes Done / Skipped list views, restore
flows, settings, persistence beyond the current browser session, GitHub
integration, CLI behavior, Rust backend commands, Tauri packaging, SQLite
storage, and additional task card fields.

## Rejected Alternatives

- Put Done and Skipped inside the 2x2 matrix: this would conflict with the
  functional requirement that the matrix areas are the four Eisenhower areas and
  that Done / Skipped are auxiliary areas outside the matrix.
- Show Done and Skipped cards in their side areas after drop: this would add
  v1 list views for terminal states, which are explicitly out of scope.
- Provide a global task creation control: this would force an extra target-area
  selection step and would not match the requirement that each matrix area has
  its own `+` creation flow.
- Include description, due date, assignee, labels, priority, timestamps, or
  GitHub issue fields on cards: these fields are outside the v1 task card
  display scope.

## Consequences

- Implementers can verify all six areas and terminal drop behavior from a
  single low-fidelity document.
- The wireframe keeps creation local to matrix areas and avoids adding a
  separate task intake concept for v1.
- Done and Skipped remain terminal status transitions in v1 rather than visible
  lists, so restore and terminal list behavior must be designed separately if
  they become future scope.
- The wireframe stays aligned with the current browser-session-only persistence
  model and does not imply product runtime changes outside the Matrix MVP page.
