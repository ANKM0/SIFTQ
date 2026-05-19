---
codd:
  node_id: design:branch-strategy-adr
  type: design
  status: draft
  depends_on:
    - id: req:yoriwake-system
      relation: depends_on
      semantic: governance
  depended_by:
    - id: design:branch-strategy
      relation: depends_on
      semantic: decision
---

# ADR 0001: Branch Strategy

## Status

Accepted.

## Context

Yoriwake needs a consistent branch workflow so issue work remains traceable,
reviewable, and easy to merge. The repository already uses GitHub issues, pull
requests, and CoDD checks, so the branch strategy should keep those practices
aligned.

## Decision

Use short-lived issue branches created from `main`. Each branch represents one
GitHub issue and uses the format:

```text
issue-<issue-number>-<short-kebab-description>
```

Finished work is pushed to `origin` and reviewed through a pull request
targeting `main`. The branch is merged into `main` after review and required
checks pass.

## Consequences

- Issue work is isolated from `main` until it is reviewed.
- Branch names make the issue relationship visible in GitHub and local Git.
- Pull requests become the standard place to review changes and CI results.
- Long-running work should be split into smaller issue branches when possible.
