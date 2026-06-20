---
name: merge-readiness
description: Decide whether a SIFTQ branch or pull request is ready to merge. Use when the user asks if a PR can be merged, whether a branch is merge-ready, final approval, release readiness, or a pre-merge gate that checks CI, reviews, AC/DoD, docs, tests, CoDD, and repository workflow state.
---

# Merge Readiness

## Overview

Use this skill to make a merge/no-merge recommendation for SIFTQ work. Treat
the output as a gate decision, not a general code review.

## Required Checks

1. Identify the target branch or PR and its base branch.
2. Check the working tree and diff so local uncommitted work is not ignored.
3. Confirm CI and local verification evidence:
   - `task ci` or the documented equivalent for the change scope
   - targeted tests that cover the risky behavior
   - CoDD validation when docs or graph-linked artifacts changed
4. Confirm review state:
   - unresolved review comments
   - requested changes
   - stale approvals after new commits
5. Confirm issue contract:
   - latest AC/DoD is satisfied
   - requirements/design/wireframes/ADR decisions are recorded as new,
     existing, or not needed
   - PR body and traceability mention the relevant issue and validation
6. Confirm workflow safety:
   - branch follows `docs/contributing/branch-strategy.md`
   - commits follow `docs/contributing/commit-message-format.md`
   - no force-push, hard reset, or destructive cleanup is required
   - sympohy labels and phase state are coherent if automation is involved

## Decision Format

Return one of:

- `ready to merge`
- `not ready to merge`
- `blocked pending information`

Then list the decisive evidence. Keep the answer short and action-oriented.

For `not ready to merge`, list the minimum required fixes before merge. For
`blocked pending information`, name the missing data or access needed to decide.

Do not merge, push, approve, or comment on a PR unless the user explicitly asks
for that action.
