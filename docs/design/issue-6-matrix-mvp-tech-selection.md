---
codd:
  node_id: design:issue-6-matrix-mvp-tech-selection
  type: design
  status: draft
  depends_on:
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: product
    - id: req:matrix-mvp-non-functional
      relation: depends_on
      semantic: product
    - id: design:browser-spa-v1-matrix-mvp-adr
      relation: depends_on
      semantic: decision
    - id: design:rust-tauri-v2-local-application-adr
      relation: depends_on
      semantic: decision
    - id: design:react-typescript-vite-matrix-ui-adr
      relation: depends_on
      semantic: decision
    - id: design:frontend-port-adapter-boundary-adr
      relation: depends_on
      semantic: decision
    - id: design:dnd-kit-matrix-drag-and-drop-adr
      relation: depends_on
      semantic: decision
  depended_by:
    - id: design:issue-12-ci-cd
      relation: depends_on
      semantic: tool-selection
    - id: design:pnpm-frontend-package-manager-adr
      relation: depends_on
      semantic: tool-selection
---

# Issue 6 Matrix MVP Technology Selection

## Context

Issue 6では、Yoriwakeの機能要件、非機能要件、技術選定を定義する。
プロダクトの方向性としては、GUIとCLIのインターフェース、DBに保存される
タスク、GitHub連携を持つローカルアプリケーションを想定している。
一方でv1 MVPの目的はより狭く、ユーザーがタスクを作成し、カードとして
確認し、2次元マトリックスの象限間をドラッグアンドドロップで移動できる
UIを検証することである。

## Selected Approach

v1のマトリックスUI検証MVPでは、ブラウザSPAを使用する。frontendは、
後からTauriのdesktop shellへ移せる構成にする。v2以降のローカル
アプリケーション作業では、CLI、SQLite、GitHub連携が実装スコープに
入るため、RustとTauriをターゲットにする。

## Technology Choices

| Area | Selection | Timing |
| --- | --- | --- |
| v1 application shape | Browser SPA | v1 MVP |
| v2 target application shape | RustとTauriによるローカルアプリ | v2 MVP以降 |
| UI foundation | React, TypeScript, Vite | v1 MVP |
| Drag and drop | dnd-kit | v1 MVP |
| Data boundary | in-memory adapterを持つTask repository port | v1 MVP |
| Persistence | 後続判断 | v2 MVP以降 |
| CLI | 後続判断 | v2 MVP以降 |
| GitHub integration | 後続判断 | v2 MVP以降 |

## Language and Framework Selection

v1 MVPでは、UI検証に必要な言語とframeworkだけを採用する。v2 MVP以降では、
ローカルアプリケーション、CLI、DB、GitHub連携に必要な言語とframeworkを
追加する。

| Area | Selection | Reason |
| --- | --- | --- |
| v1 UI language | TypeScript | task、quadrant、repository interfaceの境界を型で表現し、Tauri移植時の変更範囲を抑えるため。 |
| v1 UI framework | React | matrix page、quadrant、task card、task creation formをcomponent単位で分離しやすいため。 |
| v1 build tool | Vite | SPAのfeedback loopが速く、後続のTauri frontendとしても利用しやすいため。 |
| v1 DnD framework | dnd-kit | React上でtask cardのdrag and dropを検証しやすく、DnD logicをUI interaction layerに閉じ込めやすいため。 |
| v2 core language | Rust | GUIとCLIで共有するapplication logic、SQLite連携、GitHub連携をローカルで安全に実装しやすいため。 |
| v2 desktop framework | Tauri | React frontendを活かしながら、Rust backend commandsを持つ軽量なローカルアプリへ移行しやすいため。 |

v1ではRust、Tauri、SQLite、GitHub API clientは実装しない。ただし、v2以降で
それらを追加できるように、v1 frontendはdomain、application、ports、
adapters、uiを分けて設計する。

## Rationale

v1 MVPでは、もっともリスクの高いUI上の問いに早く答える必要がある。
その問いは、マトリックスとドラッグアンドドロップの操作感が有用かどうか
である。この検証にはブラウザSPAで十分であり、必要になる前にローカル
アプリケーションのpackaging、Rust command bindings、database migrations、
token storage、sync semanticsを導入しなくてよい。

長期的なarchitectureは引き続きRustとTauriを指向する。計画している
アプリケーションでは、ローカル実行、GUIとCLIで共有される振る舞い、
SQLite storage、GitHub synchronizationが必要になるためである。v1 frontend
にport-adapter boundaryを保つことで、マトリックスUIをその移行後も
活かせる。

## Implementation Guidance

v1 frontendでは、domain types、application operations、repository ports、
adapters、UI componentsを高凝集なmoduleに分ける。代表的な配置は次の通り。

```text
domain/
application/
ports/
adapters/
ui/
```

最初のtask repositoryはin-memoryでよい。後続のTauri repositoryは、同じ
frontend interfaceを維持したままRust commandsを呼び出せる。
