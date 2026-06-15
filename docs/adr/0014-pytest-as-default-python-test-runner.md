---
codd:
  node_id: design:pytest-as-default-python-test-runner-adr
  type: design
  status: accepted
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
---

# ADR 0014: pytest as the default Python test runner

## Status

Accepted.

## Context

The repository already has Python tests written in `unittest` style, but future test
work is expected to support faster iteration, richer fixture handling, clearer
assertion output, and simpler plugin integration.
With mixed test styles now present, the project needs one default runner and a
practical path to reduce fragmentation without forcing a disruptive big-bang
rewrite.

## Decision

SIFTQ adopts `pytest` as the standard Python test runner and style for new work.

When editing Python tests, the default policy is to write or migrate test code to
`pytest` style (`assert`, fixtures, parametrization, function-style tests where
appropriate) unless there is a clear local reason to keep the existing structure.

Existing `unittest`-style tests may remain during a transition period. They are
allowed to coexist temporarily, and no immediate bulk migration is required.

As part of edits, if a `unittest` test file is touched for any code change, test
authoring should prefer conversion to `pytest` style in that same change unless
that would significantly increase risk or scope.

## Rejected Alternatives

- Continue treating `unittest` as the default: rejected because it would preserve
  two parallel conventions and make onboarding and future refactors harder.
- Replace the repository test stack with an alternate framework: rejected because the
  cost and ecosystem impact is higher than the incremental shift to `pytest`.
- Delay any migration until full historical parity is feasible: rejected because it
  leaves new work without a clear target style and slows consistency gains.

## Consequences

- New and edited tests can increasingly use `pytest` features and ecosystem tooling
  without changing the whole suite at once.
- A temporary mixed test style will remain; contributors must respect both patterns
  until existing `unittest` tests are gradually converted.
- The repo direction is explicit: default contributions migrate toward `pytest`, while
  legacy `unittest` tests are tolerated only as a migration bridge.
