---
codd:
  node_id: design:frontend-port-adapter-boundary-adr
  type: design
  status: draft
  depends_on:
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: architecture
    - id: req:matrix-mvp-non-functional
      relation: depends_on
      semantic: architecture
  depended_by:
    - id: design:issue-6-matrix-mvp-tech-selection
      relation: depends_on
      semantic: decision
---

# ADR 0005: Frontend Port Adapter Boundary

## Status

Accepted.

## Context

v1 MVPでは、persistence、GitHub integration、Tauri commandsは不要である。
後続マイルストーンでは、Rust local applicationを通じてlocal database、
GitHub synchronization、CLI supportを追加する想定である。v1 UIがdata access
assumptionsを直接持つと、後続のmigrationで不要な書き直しが発生する。

## Decision

domain types、application operations、repository ports、adapters、UI components
を分離し、v1 frontendを疎結合に保つ。

v1実装では、task repository interfaceの背後にin-memory task repositoryを
配置する。後続実装では、matrix UI contractを変えずに、そのadapterを
Tauri-backed repositoryへ差し替えられる。

## Consequences

- matrix UIはrenderingとinteractionに対して高凝集のまま保てる。
- data access decisionsを差し替え可能にできる。
- v1 MVPではpersistenceを避けながら、後続のSQLite導入に備えられる。
- projectは小さなinterfacesを維持し、adapter detailsをUI componentsへ
  漏らさないようにする必要がある。
