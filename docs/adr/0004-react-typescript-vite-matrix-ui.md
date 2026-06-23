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
    - id: design:matrix-mvp-technology-selection
      relation: depends_on
      semantic: decision
---

# ADR 0004: React TypeScript Vite for Matrix UI

## Status

Accepted.

## Context

MVPでは、ブラウザベースのマトリックスページに対する速いfeedback loop
が必要である。UIは、型付けされたtaskとquadrant model、componentized
matrix rendering、drag-and-drop integrationを扱う必要がある。現在の方針では、
同じfrontendをbrowser-only runtimeとして継続し、storage adapterを差し替え可能に
保つ必要がある。

## Decision

v1 matrix MVPのfrontend foundationとして、React、TypeScript、Viteを使用する。

Reactは、matrix page、quadrant containers、task cards、task creation formの
component modelを提供する。TypeScriptは、taskとquadrantの境界を明示する。
Viteは軽量なdevelopment/build setupを提供し、静的browser SPAとして配布しやすい。

## Alternatives Considered

Viteは、UI検証を速く回せる唯一の選択肢として選んだわけではない。v1 MVPでは、
マトリックスUIとdrag and drop interactionを早く検証しながら、frontendを
小さく保ち、後続のTauri webviewへ移しやすいことを重視する。

- Next.jsはReactとTypeScriptでUI検証を速く始められるが、MVPでは不要な
  routing、server-side rendering、API routeの前提を持ち込みやすい。静的な
  browser SPAとして扱うにはViteのほうが小さい。
- Parcelは設定を少なく始められるが、このprojectで必要なReact、TypeScript、
  Vitestの組み合わせでは、Viteのほうが採用例とtoolingの見通しがよい。
- RspackまたはRsbuildは高速なbuild toolとして候補になるが、v1 MVPの規模では
  webpack互換性や大規模frontend向けの利点を活かす場面が少ない。
- Webpackは成熟しているが、configurationとtoolchainの重さがv1 MVPの
  feedback loopを小さく保つ方針に合いにくい。
- Create React AppはReact SPAを始める選択肢だったが、新規のReactとTypeScript
  frontend foundationとしては、Viteのほうが軽量でTauriへの移行方針にも
  合わせやすい。

## Consequences

- MVPを小さく馴染みのあるfrontend toolchainで実装できる。
- domain rules、storage adapter、UIの型を検査できる。
- React applicationをbrowser-only runtimeとして実行できる。
- 将来のstorage adapter差し替えを現実的に保つため、browser storage detailsはadapterへ隔離する。
