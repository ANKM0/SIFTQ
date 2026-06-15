---
codd:
  node_id: design:settings-repository-adapter-boundary-adr
  type: design
  status: draft
  depends_on:
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: settings-scope
    - id: req:matrix-mvp-non-functional
      relation: depends_on
      semantic: architecture
    - id: design:frontend-port-adapter-boundary-adr
      relation: depends_on
      semantic: architecture
---

# ADR 0014: Settings Repository Adapter Boundary

## Status

Accepted.

## Context

Issue #71 adds v7 settings page behavior for changing, saving, restoring, and
reusing the labels for the four matrix areas plus Done and Skipped. The current
frontend has a task repository port in `src/ports/taskRepository.ts` and an
in-memory adapter in `src/adapters/inMemoryTaskRepository.ts`. Area identities
and default labels are currently static domain data in `src/domain/area.ts`.

There is no application settings repository or SQLite adapter yet. The existing
`.sympohy/config.yaml` file configures repository-local AI runner behavior and
is not application settings storage. SQLite is also not present in the current
browser-only frontend implementation, although ADR 0003 keeps SQLite within the
future Rust/Tauri local application direction.

The v7 scope needs SQLite persistence for area labels without broadening the
task repository or letting the UI depend on infrastructure details.

## Decision

Introduce a separate settings repository port for persisted application
settings. The first settings managed by this port are area labels for the six
known `AreaId` values: `do`, `schedule`, `delegate`, `eliminate`, `done`, and
`skipped`.

The settings repository contract is responsible for:

- Loading a complete area label settings value for all known areas.
- Saving a complete, already validated area label settings value atomically.
- Restoring defaults by saving the labels derived from `INITIAL_AREAS`.
- Preserving stable area IDs; labels are mutable display text only.

The settings repository contract is not responsible for:

- Creating, deleting, reordering, or changing the kind of areas.
- Storing tasks, task ordering, or task status.
- Knowing React component state, routing, drag-and-drop behavior, or form UI
  details.
- Owning GitHub synchronization or CLI behavior.

Application and domain code own label semantics. They normalize labels by
trimming user input, reject labels that become empty, keep duplicate labels
allowed unless a later requirement says otherwise, and decide when default
labels should be written. The repository port should expose only values that
have passed those rules.

The SQLite adapter is responsible for mapping the settings repository contract
to durable local storage. It owns schema creation or migrations, transactions,
row serialization, row ordering independence, and conversion between SQLite
rows and the complete settings value. Missing rows for known areas are treated
as defaults during load so a new or partially migrated database can still
produce a complete settings value. SQLite constraints may reject impossible
storage states, but they are a backstop rather than the primary source of
business validation.

The UI must depend on application operations and the settings repository port,
not on the SQLite adapter directly. Tests for application behavior should use an
in-memory settings repository. Tests for persistence should target the SQLite
adapter through the settings repository contract.

## Rejected Alternatives

- Extend the task repository with area label settings. This mixes task
  lifecycle storage with user preference storage and makes future task
  persistence harder to evolve independently.
- Store labels directly from React components through a SQLite or browser
  storage API. This bypasses the port-adapter boundary from ADR 0005 and makes
  validation and default restoration harder to test outside the UI.
- Put label validation primarily in the SQLite adapter. This duplicates
  business rules in infrastructure and makes in-memory tests less representative
  of production behavior.

## Consequences

- v7 can add settings UI and SQLite persistence without changing task repository
  responsibilities.
- The app keeps one stable source of truth for area identity while allowing
  display labels to change.
- Adapter tests need to cover default loading, full save and reload, invalid
  storage backstops, and partial database migration behavior.
- A later implementation still needs to choose the concrete SQLite runtime and
  file location within the Rust/Tauri application boundary.
