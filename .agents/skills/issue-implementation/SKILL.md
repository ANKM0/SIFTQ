---
name: issue-implementation
description: Follow the SIFTQ issue implementation workflow for repository code, test, documentation, branch, commit, push, and PR work. Use when implementing or fixing a GitHub issue, changing source files, adding tests, preparing commits, or validating work against SIFTQ development docs.
---

# Issue Implementation

## Overview

Use this skill to carry SIFTQ issue work through implementation with the
repository docs as the source of truth. Do not duplicate the commit or branch
rules in this skill; load the docs listed below when those rules matter.

## Docs To Read

Read the relevant core docs before acting:

- `docs/contributing/development-flow.md` for the implementation stage gates.
- `docs/contributing/assets/development-flow.mmd` when the flow details are
  needed beyond the rendered overview.
- `docs/contributing/branch-strategy.md` before creating, naming, pushing, or
  merging a branch.
- `docs/contributing/commit-message-format.md` before creating, reviewing, or
  suggesting a commit message.
- Feature-specific `docs/requirements/`, `docs/design/`, `docs/wireframes/`,
  and `docs/adr/` files that are linked from the issue, AC/DoD, or changed
  code.

Read `docs/loop-engineering.md` when using or updating taqt issue automation,
stale-run recovery, labels, watcher behavior, or review/merge automation.

Use `.agents/skills/feature-docs-planning/` before implementation when the
requirements, design, wireframe, or ADR handling has not been decided.

## Workflow

1. Identify the GitHub issue and latest AC/DoD.
2. Confirm requirements, design, wireframes, and ADR handling is recorded.
3. Read the current implementation area before editing.
4. Create or use the issue branch according to
   `docs/contributing/branch-strategy.md`.
5. Implement focused code, docs, and tests for the issue only.
6. Run the smallest meaningful verification first, then the repository gate
   required by the development flow.
7. Commit with the format in `docs/contributing/commit-message-format.md`.
8. Push, open or update the PR, and keep review notes and validation evidence
   traceable to the issue.

## Guardrails

- Keep the implementation scoped to one issue unless the issue has been split.
- Prefer existing architecture, helpers, tests, and docs over new conventions.
- Do not treat this skill as the source for branch or commit rules; those rules
  live in `docs/contributing/`.
- If docs and code disagree, surface the mismatch and update or cite the right
  source before proceeding.
