---
codd:
  node_id: design:real-sqlite-test-strategy-adr
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
---

# ADR 0017: Real SQLite Test Strategy

## Status

Superseded by ADR 0018.

## Supersession Note

#59 は SQLite を使わない browser-only persistence へ変更されたため、このADRの
real SQLite test strategy は現行 #59 のテスト方針ではない。browser storage の
repository / UI tests は `ADR 0018` と
`docs/design/matrix-mvp-v2-browser-storage-design.md` に従う。

## Context

Issue #59 adds SQLite schema, migration, command boundaries, and terminal task
behavior to the Matrix app. Pure mocks would not exercise the actual migration
paths, schema constraints, or transaction behavior that now matter to the
product.

The project needs a test approach that favors realistic boundary coverage while
still keeping the core behavior deterministic and fast enough for routine
development.

## Decision

Use real SQLite in `app-core` tests and boundary tests.

The core test suite should exercise the repository and service layers against a
real temporary SQLite database, including reopen tests for persistence and
migration checks. Deterministic tests may inject a stable UUID generator, but
the database itself should not be faked.

Command and handler tests should also use real `app-core` plus a temporary
SQLite database so structured errors, startup failures, and schema mismatches
are observed through the same path the app uses.

## Rejected Alternatives

- Mock SQLite or replace it with an in-memory repository for the core tests.
  That would miss migration failures, constraint issues, and transaction
  mistakes.
- Test only through the frontend. That would hide backend schema and command
  boundary regressions until manual verification.
- Put all confidence in browser-level smoke tests. That is too high-level for
  storage and migration regressions.

## Consequences

- Persistence, migration, and command boundary bugs are caught closer to the
  real runtime.
- The test suite is slightly heavier because it touches temporary files and
  real SQLite connections.
- Test setup must keep deterministic ID generation available where needed.
- The approach aligns `app-core` with the long-lived source of truth for data
  behavior instead of treating SQLite as a mockable detail.
