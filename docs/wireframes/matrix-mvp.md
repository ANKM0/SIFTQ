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

# Matrix MVP Wireframe

## Scope

This wireframe describes the v1 Matrix MVP single-screen layout only. It follows
`docs/requirements/matrix-mvp-functional-requirements.md` and does not add
runtime behavior outside the documented v1 scope.

The screen contains six areas:

- `Skipped`: terminal drop area on the left side of the matrix.
- `Do`: matrix area for important and urgent tasks.
- `Schedule`: matrix area for important and not urgent tasks.
- `Delegate`: matrix area for not important and urgent tasks.
- `Eliminate`: matrix area for not important and not urgent tasks.
- `Done`: terminal drop area on the right side of the matrix.

## Default Layout

```text
+----------------+  +----------------+  +----------------+  +----------------+
| Skipped        |  | Do          [+] |  | Schedule    [+] |  | Done           |
|                |  |                |  |                |  |                |
| Drop task here |  | [Task card A]  |  | [Task card C]  |  | Drop task here |
| to skip it.    |  | [Task card B]  |  |                |  | to complete it.|
|                |  |                |  |                |  |                |
|                |  +----------------+  +----------------+  |                |
|                |  +----------------+  +----------------+  |                |
|                |  | Delegate   [+] |  | Eliminate  [+] |  |                |
|                |  |                |  |                |  |                |
|                |  | [Task card D]  |  | [Task card E]  |  |                |
|                |  |                |  | [Task card F]  |  |                |
+----------------+  +----------------+  +----------------+  +----------------+
```

Layout rules:

- The four matrix areas are arranged as a 2x2 grid.
- `Skipped` is a tall rectangular drop area to the left of the 2x2 grid.
- `Done` is a tall rectangular drop area to the right of the 2x2 grid.
- Each matrix area header includes a `+` creation control.
- `Skipped` and `Done` do not expose a `+` creation control.
- Task cards show the task `title` only.
- Internal task fields `id`, `areaId`, `status`, and `order` are not displayed
  on the card.

## Task Creation

Each matrix area has its own creation entry point.

```text
+----------------+
| Do          [+] |
|                |
| Title input    |
| [Create]       |
|                |
| [Task card A]  |
| [Task card B]  |
+----------------+
```

Creation rules:

- Activating `+` opens or focuses the title input for that matrix area.
- The user enters a task title in the target area.
- The created task appears at the bottom of that same area.
- Empty titles after trim remain invalid.
- Titles longer than 256 characters remain invalid.
- Duplicate titles are allowed and do not show a duplicate warning.

## Area Internal Reorder

Dragging a card within the same matrix area changes only that area's visible
order.

```text
Before drag in Do:
+----------------+
| Do          [+] |
| [Task card A]  |
| [Task card B]  |
| [Task card C]  |
+----------------+

After dragging Task card C above Task card A:
+----------------+
| Do          [+] |
| [Task card C]  |
| [Task card A]  |
| [Task card B]  |
+----------------+
```

Reorder rules:

- The task remains active.
- The task remains in the same matrix area.
- The new order is kept for the current browser session.

## Matrix Area Move

Dragging a card from one matrix area to another moves the card to the target
matrix area and keeps it visible in the matrix.

```text
Before drag:
+----------------+  +----------------+
| Do          [+] |  | Schedule    [+] |
| [Task card A]  |  | [Task card C]   |
| [Task card B]  |  |                 |
+----------------+  +----------------+

After dragging Task card B to Schedule:
+----------------+  +----------------+
| Do          [+] |  | Schedule    [+] |
| [Task card A]  |  | [Task card C]   |
|                |  | [Task card B]   |
+----------------+  +----------------+
```

Move rules:

- The task remains active.
- The task's `areaId` changes to the target matrix area.
- The moved task is placed in the target area's visible order.
- The new area and order are kept for the current browser session.

## Done Drop

Dropping a matrix task on `Done` is a terminal status update, not a visible
reorder into the right-side area.

```text
Before drag:
+----------------+  +----------------+
| Do          [+] |  | Done           |
| [Task card A]  |  | Drop task here |
| [Task card B]  |  | to complete it.|
+----------------+  +----------------+

After dragging Task card B to Done:
+----------------+  +----------------+
| Do          [+] |  | Done           |
| [Task card A]  |  | Drop task here |
|                |  | to complete it.|
+----------------+  +----------------+
```

Done rules:

- The dropped task status becomes `done`.
- The dropped task is removed from the normal matrix display.
- v1 does not show a Done task list.
- v1 does not provide restore from Done.

## Skipped Drop

Dropping a matrix task on `Skipped` is a terminal status update, not a visible
reorder into the left-side area.

```text
Before drag:
+----------------+  +----------------+
| Skipped        |  | Eliminate   [+] |
| Drop task here |  | [Task card E]   |
| to skip it.    |  | [Task card F]   |
+----------------+  +----------------+

After dragging Task card E to Skipped:
+----------------+  +----------------+
| Skipped        |  | Eliminate   [+] |
| Drop task here |  | [Task card F]   |
| to skip it.    |  |                 |
+----------------+  +----------------+
```

Skipped rules:

- The dropped task status becomes `skipped`.
- The dropped task is removed from the normal matrix display.
- v1 does not show a Skipped task list.
- v1 does not provide restore from Skipped.

## Review Notes

- Confirm that all six areas are visible on one Matrix MVP screen.
- Confirm that `Skipped` and `Done` are terminal drop targets outside the 2x2
  matrix, not regular matrix areas.
- Confirm that each matrix area exposes `+` and terminal areas do not.
- Confirm that cards leaving the matrix through `Done` or `Skipped` disappear
  from the normal matrix display.
- Confirm that no v1 out-of-scope fields are shown on task cards.

## Known Constraints

- State is kept only for the current browser session.
- Done and Skipped tasks are hidden from the v1 normal display.
- This wireframe does not define final visual styling, spacing tokens,
  animation, keyboard DnD, or mobile/touch DnD behavior.

## v1 Out of Scope

- Done / Skipped list views.
- Restore from Done / Skipped.
- Persistence outside memory for the current browser session.
- Settings page or area label editing.
- GitHub Issues or GitHub Projects integration.
- CLI, Rust backend commands, Tauri desktop packaging, and SQLite storage.
- Task fields other than the title on cards.
