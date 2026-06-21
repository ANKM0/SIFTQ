---
codd:
  node_id: design:sqlite-tauri-rust-backend-boundary-adr
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
---

# ADR 0016: SQLite, Tauri, and Rust Backend Boundary

## Status

Accepted.

## Context

Issue #59 moves the Matrix UI from browser-only session state to a desktop app
with persistent SQLite storage. The app must still reuse the React frontend, but
the storage and application rules need to live behind a Rust core so that future
CLI and desktop flows can share the same behavior.

The project also needs a clear contract story. For #59 the frontend and Rust
contracts are hand-written. That keeps the migration small while the Rust core,
SQLite schema, and Tauri command surface are still settling.

## Decision

Use Rust as the application core behind Tauri, and keep all SQLite access inside
`app-core`.

`desktop-app` only owns the Tauri shell, startup, and command adapter. It must
not depend on SQLite implementation details directly.

Hand-write the FE/Rust command contract for #59. Place the TypeScript contract
types in `src/contracts/*`, align Tauri DTOs with `serde(rename_all =
"camelCase")`, and keep a short `MEMO` near the contract definitions that says
the contract may later be replaced by generated TypeScript types from Rust.

The backend storage model for #59 keeps terminal tasks in the `done` / `skipped`
areas. The later #63 migration will change that model so terminal tasks retain
their matrix `area_id` and only `status` changes.

## Rejected Alternatives

- Let `desktop-app` talk to SQLite directly. That would blur the backend
  boundary, duplicate persistence concerns, and make CLI reuse harder.
- Generate TypeScript contracts immediately. That would add toolchain and schema
  coupling before the Rust core and command surface are stable.
- Keep persistence in the browser layer. That would reintroduce session-bound
  storage and block the desktop app goal.

## Consequences

- `app-core` becomes the single place for SQLite schema, migration, and
  application rules.
- `desktop-app` stays thin and can focus on Tauri lifecycle and structured error
  mapping.
- Contract changes remain explicit and easy to review during the #59 migration.
- A second migration is expected in #63 when terminal tasks move to
  status-only transitions with matrix `area_id` retention.
- Later Rust-to-TypeScript contract generation can replace the hand-written
  contract layer without changing the core ownership model.
