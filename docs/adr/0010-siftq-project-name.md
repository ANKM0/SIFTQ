---
codd:
  node_id: design:siftq-project-name-adr
  type: design
  status: accepted
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
---

# ADR 0010: SIFTQ Project Name

## Status

Accepted.

## Context

The project needs a stable product and repository name before references spread
across documentation, package metadata, local tooling, and release assets.
The name must fit a GitHub Issue triage tool with a smooth matrix UI, while
remaining concise enough for repository, package, and future CLI usage.

## Decision

Use `SIFTQ` as the project display name and GitHub repository name.

`SIFTQ` expands to:

```text
Smooth Issue Filtering & Triage Queue
```

Use `siftq` for lowercase machine names, including npm package name, Python
project name, future CLI name, import-oriented identifiers, and local tooling
references.

Use `siftq-base.tar` as the WSL template asset filename. Keep the existing
`Yoriwake-base` release tag unchanged so previously published release references
remain stable.

## Rejected Alternatives

- The previous Japanese-derived name: matched the initial "selection/sorting"
  concept, but the project later prioritized a shorter developer-tool name that
  directly signals issue filtering, triage, and queue handling in English.
- `SIFT`: concise and conceptually close, but it conflicts with existing
  product and package names. Adding `Q` preserves the "sift" concept while
  making the project name more distinctive.
- `FLIT`, `GLIT`, `NITQ`, `TRIQ`, `SLIQ`, `FLIQ`, `FURUI`, and `FURUQ`: each
  captured part of the intended experience, but none balanced issue triage,
  filtering, smooth interaction, queue semantics, and developer-tool naming as
  well as `SIFTQ`.

## Consequences

- Product-facing documentation and UI use `SIFTQ`.
- Package metadata and future command examples use `siftq`.
- Repository URLs and clone instructions point at `ANKM0/SIFTQ`.
- WSL setup documentation refers to the `siftq-base.tar` asset while preserving
  the `Yoriwake-base` release tag.
- Existing documentation and local tooling references must stop using the old
  project name except where explicitly referring to the unchanged release tag.
