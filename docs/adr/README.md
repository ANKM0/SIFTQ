---
codd:
  node_id: design:adr-index
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:adr-authoring
      relation: depends_on
      semantic: index
---

# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for long-lived
SIFTQ workflow, governance, and architecture decisions.

## ADRs

| ADR | Title | Status |
| --- | --- | --- |
| [0001](./0001-branch-strategy.md) | Branch Strategy | Accepted |
| [0002](./0002-browser-spa-v1-matrix-mvp.md) | v1 Matrix MVPのBrowser SPA採用 | Accepted |
| [0003](./0003-rust-tauri-v2-local-application.md) | v2 Local ApplicationのRust and Tauri採用 | Accepted |
| [0004](./0004-react-typescript-vite-matrix-ui.md) | Matrix UIのReact TypeScript Vite採用 | Accepted |
| [0005](./0005-frontend-port-adapter-boundary.md) | Frontend Port Adapter Boundary採用 | Accepted |
| [0006](./0006-dnd-kit-matrix-drag-and-drop.md) | Matrix Drag and Dropのdnd-kit採用 | Accepted |
| [0007](./0007-pnpm-frontend-package-manager.md) | Frontend Package Managerのpnpm採用 | Accepted |
| [0008](./0008-github-actions-ci-cd-toolchain.md) | GitHub Actions CI/CD Toolchain採用 | Accepted |
| [0009](./0009-taskfile-command-runner.md) | Command RunnerのTaskfile採用 | Accepted |
| [0010](./0010-siftq-project-name.md) | SIFTQ Project Name | Accepted |
| [0011](./0011-takt-ticket-driven-ai-runner.md) | TAKT for Ticket-Driven AI Runner | Accepted |
| [0012](./0012-matrix-mvp-wireframe-layout.md) | Matrix MVP Wireframe Layout | Accepted |
