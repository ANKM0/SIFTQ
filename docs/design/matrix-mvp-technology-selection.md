---
codd:
  node_id: design:matrix-mvp-technology-selection
  type: design
  status: implemented
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
    - id: design:ci-cd-foundation
      relation: depends_on
      semantic: tool-selection
    - id: design:pnpm-frontend-package-manager-adr
      relation: depends_on
      semantic: tool-selection
    - id: design:github-actions-ci-cd-toolchain-adr
      relation: depends_on
      semantic: tool-selection
---

# Matrix MVP 技術選定設計

## 背景

Matrix MVP技術選定では、SIFTQの機能要件、非機能要件、技術選定を定義する。
プロダクトの方向性としては、GUIとCLIのインターフェース、DBに保存される
タスク、GitHub連携を持つローカルアプリケーションを想定している。
一方でv1 MVPの目的はより狭く、ユーザーがタスクを作成し、カードとして
確認し、2次元マトリックスの象限間をドラッグアンドドロップで移動できる
UIを検証することである。

## 採用方針

v1のマトリックスUI検証MVPでは、ブラウザSPAを使用する。frontendは、
後からTauriのdesktop shellへ移せる構成にする。v2以降のローカル
アプリケーション作業では、CLI、SQLite、GitHub連携が実装スコープに
入るため、RustとTauriをターゲットにする。

## 技術選定

| 領域 | 選定 | 時期 |
| --- | --- | --- |
| v1 application形態 | Browser SPA | v1 MVP |
| v2目標application形態 | RustとTauriによるローカルアプリ | v2 MVP以降 |
| UI基盤 | React, TypeScript, Vite | v1 MVP |
| drag and drop | dnd-kit | v1 MVP |
| data境界 | in-memory adapterを持つTask repository port | v1 MVP |
| 永続化 | 後続判断 | v2 MVP以降 |
| CLI | 後続判断 | v2 MVP以降 |
| GitHub連携 | 後続判断 | v2 MVP以降 |

## 言語・フレームワーク選定

v1 MVPでは、UI検証に必要な言語とframeworkだけを採用する。v2 MVP以降では、
ローカルアプリケーション、CLI、DB、GitHub連携に必要な言語とframeworkを
追加する。

| 領域 | 選定 | 理由 |
| --- | --- | --- |
| v1 UI言語 | TypeScript | task、quadrant、repository interfaceの境界を型で表現し、Tauri移植時の変更範囲を抑えるため。 |
| v1 UI framework | React | matrix page、quadrant、task card、task creation formをcomponent単位で分離しやすいため。 |
| v1 build tool | Vite | SPAのfeedback loopが速く、後続のTauri frontendとしても利用しやすいため。 |
| v1 DnD framework | dnd-kit | React上でtask cardのdrag and dropを検証しやすく、DnD logicをUI interaction layerに閉じ込めやすいため。 |
| v2中核言語 | Rust | GUIとCLIで共有するapplication logic、SQLite連携、GitHub連携をローカルで安全に実装しやすいため。 |
| v2 desktop framework | Tauri | React frontendを活かしながら、Rust backend commandsを持つ軽量なローカルアプリへ移行しやすいため。 |

v1ではRust、Tauri、SQLite、GitHub API clientは実装しない。ただし、v2以降で
それらを追加できるように、v1 frontendはdomain、application、ports、
adapters、uiを分けて設計する。

## 判断理由

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

## 実装指針

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

MVP実装のfrontend entrypointは `src/main.tsx` とし、React/Vite固有のambient
typeは `src/vite-env.d.ts` に閉じる。`src/main.tsx` からUI componentへ入り、
UI componentのimport graphを通じてdomain、application、ports、adapters、
interaction layer、対応テストへtraceできる構成にする。

## 完了トレーサビリティ

Matrix MVP v1は、browser SPA、React/TypeScript/Vite、dnd-kit、in-memory
repository port/adapterの構成で実装済みである。完了範囲は次の実装単位に
対応する。

- domain model: `src/domain/area.ts`、`src/domain/task.ts`
- application operations: `src/application/taskOperations.ts`
- port/adapter boundary: `src/ports/taskRepository.ts`、
  `src/adapters/inMemoryTaskRepository.ts`
- UI and interaction layer: `src/ui/App.tsx`、`src/ui/App.css`、
  `src/ui/dragDrop.ts`
- entrypoint and Vite types: `src/main.tsx`、`src/vite-env.d.ts`
- tests: `tests/domain/task.test.ts`、`tests/application/taskOperations.test.ts`、
  `tests/adapters/inMemoryTaskRepository.test.ts`、`tests/ui/App.test.tsx`、
  `tests/ui/dragDrop.test.ts`

v1 scope外の永続化、GitHub連携、Tauri化、CLI、設定ページ、公開URL、
PR preview URL、キーボードDnD完成対応、モバイル / タッチDnD最適化は
実装していない。これらはv2以降の判断対象としてrequirements側のfuture scopeに
残す。
