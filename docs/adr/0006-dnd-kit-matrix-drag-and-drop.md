---
codd:
  node_id: design:dnd-kit-matrix-drag-and-drop-adr
  type: design
  status: draft
  depends_on:
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: interaction
    - id: req:matrix-mvp-non-functional
      relation: depends_on
      semantic: interaction
  depended_by:
    - id: design:issue-6-matrix-mvp-tech-selection
      relation: depends_on
      semantic: decision
---

# ADR 0006: dnd-kit for Matrix Drag and Drop

## Status

Accepted.

## Context

v1 MVPの中心的なinteractionは、task cardsをmatrix quadrants間でdrag and
dropして移動することである。実装では、大きなapplication frameworkや
browser-specific data persistence approachに縛られず、応答性のある
interaction modelを支える必要がある。

## Decision

v1 matrixのdrag-and-drop interactionにはdnd-kitを使用する。

dnd-kitはReactのdrag-and-drop behaviorに焦点を当てており、matrix、
quadrant、task cardのcomponent boundariesで統合できる。これにより、
persistenceやbackend concernsをdrag-and-drop layerの外側に置いたまま、
MVPでinteractionを検証できる。

## Consequences

- v1 MVPでは、drag and drop behaviorを自前実装するのではなく、主要な
  interactionの検証に集中できる。
- drag-and-drop logicをUI interaction layer内に留められる。
- repositoryとdomain boundariesは、選定したDnD libraryから独立したまま
  保てる。
- 後からaccessibility、keyboard、mobile interaction requirementsで不足が
  見えた場合、この選定を再検討する。
