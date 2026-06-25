---
codd:
  node_id: design:browser-only-matrix-runtime-storage-adr
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: req:matrix-mvp-v2-browser-storage
      relation: depends_on
      semantic: storage
  depended_by:
    - id: design:matrix-mvp-technology-selection
      relation: depends_on
      semantic: decision
    - id: design:matrix-mvp-v2-browser-storage
      relation: depends_on
      semantic: decision
---

# ADR 0018: Browser-Only Matrix Runtime and Storage

## Status

Accepted.

## Context

Issue #59 originally targeted a Rust/Tauri desktop app with SQLite storage so
that a future CLI could share the same core. The product direction changed:
CLI is additional content, while the immediate requirement is that the Matrix
UI works in a browser, can be used from another device through browser-first
delivery, and remains usable on the user's PC without a native app install.

The current Matrix interaction workload is small. Smooth task movement is
driven by React render behavior, dnd-kit, CSS transforms, and DOM size rather
than by a Rust backend.

## Decision

Use a browser-only runtime for the Matrix MVP v2 persistence step.

The app remains React, TypeScript, Vite, and dnd-kit. Task persistence lives
behind the frontend `TaskRepository` port and uses browser storage for #59.
Rust, Tauri, SQLite, native filesystem access, and CLI shared-core work are
not part of the #59 runtime.

The storage contract is the existing frontend task shape:

- `id`
- `title`
- `areaId`
- `status`
- `order`

The browser storage adapter owns read/write, validation, ordering
normalization, and browser reload persistence. Later sync or larger local data
needs may replace the adapter with IndexedDB, OPFS, or a remote API without
changing the Matrix UI contract.

## Rejected Alternatives

- Keep Rust/Tauri/SQLite for #59: this supports a native local app and future
  CLI sharing, but it blocks browser-only use and adds native build/toolchain
  requirements before CLI is part of the product scope.
- Browser and Tauri in parallel for #59: this keeps both distribution paths
  open, but it doubles smoke and CI surface before the browser-first behavior
  is stable.
- Browser-only with in-memory storage: this keeps implementation smaller, but
  it fails the persistence goal after browser reload.

## Consequences

- Users can run and test the Matrix app through a browser without Tauri.
- The local development and CI toolchain no longer needs Rust, cargo-tauri, or
  WebKitGTK dependencies for #59.
- Browser reload persistence is required evidence for storage changes.
- CLI, native filesystem access, desktop packaging, SQLite, and app restart
  persistence move to later issues if they become product requirements.
- localStorage is sufficient for the current Matrix MVP size, but larger data,
  multi-device sync, or stronger transactional semantics should trigger a
  follow-up storage ADR.
