---
codd:
  node_id: design:react-typescript-vite-matrix-ui-adr
  type: design
  status: draft
  depends_on:
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: ui
    - id: req:matrix-mvp-non-functional
      relation: depends_on
      semantic: ui
  depended_by:
    - id: design:issue-6-matrix-mvp-tech-selection
      relation: depends_on
      semantic: decision
---

# ADR 0004: React TypeScript Vite for Matrix UI

## Status

Accepted.

## Context

v1 MVPでは、ブラウザベースのマトリックスページに対する速いfeedback loop
が必要である。UIは、型付けされたtaskとquadrant model、componentized
matrix rendering、drag-and-drop integrationを扱う必要がある。同じfrontend
は、後続マイルストーンでTauri shellへ移植できる必要がある。

## Decision

v1 matrix MVPのfrontend foundationとして、React、TypeScript、Viteを使用する。

Reactは、matrix page、quadrant containers、task cards、task creation formの
component modelを提供する。TypeScriptは、taskとquadrantの境界を明示する。
Viteは軽量なdevelopment/build setupを提供し、後からTauriのfrontend要件にも
合わせやすい。

## Consequences

- v1 MVPを小さく馴染みのあるfrontend toolchainで実装できる。
- Rust integrationを追加する前に、domainとUIの型を検査できる。
- React applicationは後からTauri webview内で実行できる。
- 将来のTauri integrationを現実的に保つため、browser-only APIsは隔離する。
