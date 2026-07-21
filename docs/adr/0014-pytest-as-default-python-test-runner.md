---
codd:
  node_id: design:pytest-as-default-python-test-runner-adr
  type: design
  status: accepted
  depends_on:
  - id: req:repository-governance
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

## Reviewability (SIFTQ-89 logical step 7)

### Why this migration is happening

- This ADR is the source of record for the pytest migration rationale and scope.
- The Taskfile wiring is the implementation anchor used for PR review:
  - `Taskfile.yml` task `pytest` runs `uv run python -m pytest`.
  - `Taskfile.yml` task `ci:test` executes `task pytest`.

### AC/DoD mapping for step 7 review

- Step 7 request: "Use ADR decision + explicit Taskfile diff as review anchor."
  - Evidence: `docs/adr/0014-pytest-as-default-python-test-runner.md` and the `pytest` + `ci:test` task definitions in `Taskfile.yml`.
- Step 7 request: "Ensure PR review can verify each AC/DoD item by mapping to ADR and changed task commands."
  - Evidence: This section now links each AC/DoD intent to the exact Taskfile commands reviewers should inspect.
