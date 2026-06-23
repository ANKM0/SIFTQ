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
    - id: design:matrix-mvp-technology-selection
      relation: depends_on
      semantic: decision
---

# ADR 0005: Frontend Port Adapter Boundary

## Status

Accepted.

## Context

MVPでは、browser storage persistenceを使う一方で、GitHub integrationやCLIは
不要である。UIがdata access assumptionsを直接持つと、後続のIndexedDB、OPFS、
remote API、GitHub synchronizationへの移行で不要な書き直しが発生する。

## Decision

domain types、application operations、repository ports、adapters、UI components
を分離し、v1 frontendを疎結合に保つ。

本番実装では、task repository interfaceの背後にbrowser storage repositoryを
配置する。後続実装では、matrix UI contractを変えずに、そのadapterを
IndexedDB、OPFS、remote API、GitHub synchronizationなどへ差し替えられる。

## Consequences

- matrix UIはrenderingとinteractionに対して高凝集のまま保てる。
- data access decisionsを差し替え可能にできる。
- browser storage persistenceを追加しながら、後続のstorage移行に備えられる。
- projectは小さなinterfacesを維持し、adapter detailsをUI componentsへ
  漏らさないようにする必要がある。
