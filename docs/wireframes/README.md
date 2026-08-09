# Zero-base Task Wireframes

This directory contains the new low-fidelity wireframes for the zero-base task
redesign.

- `task-redesign.md`: wireframe contract.
- `index.html`: state map and links to each wireframe state.
- `matrix-page.html`: matrix page with drag and drop task cards.
- `task-list.html`: GitHub Issues-like task list page.
- `task-detail.html`: task detail page with title, description, and status.
- `task-new.html`: new task creation state.
- `task-status-menu.html`: task detail state with status popover open.
- `task-area-menu.html`: task detail state with area popover open.
- `task-redesign.css`: shared low-fidelity styling.

Status is `do`, `done`, or `skip`. Area is always `1`, `2`, `3`, or `4`.
The matrix page renders only `do` tasks grouped by area; `skip` and `done`
remain visible in list/detail states and keep their area.
