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
一方でv1 MVPの目的はより狭く、利用者がタスクを作成し、カードとして
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

Matrix MVP v1で検証したbrowser SPA、React/TypeScript/Vite、dnd-kit、
repository port/adapterの構成は、v2 migrationでSQLite/Tauri構成へ移行した。
現在の完了範囲は次の実装単位に対応する。

- Rust domain/application/storage: `crates/core/src/domain.rs`、
  `crates/core/src/service.rs`、`crates/core/src/repository.rs`、
  `crates/core/src/sqlite.rs`、`crates/core/src/id.rs`、
  `crates/core/src/error.rs`
- Tauri command boundary: `src-tauri/src/lib.rs`、`src-tauri/src/main.rs`
- frontend contract and adapter boundary: `src/contracts/task.ts`、
  `src/ports/taskRepository.ts`、`src/adapters/tauriTaskRepository.ts`、
  `src/adapters/tauriInvoke.ts`
- UI and interaction layer: `src/ui/App.tsx`、`src/ui/App.css`、
  `src/ui/taskPresentation.ts`、`src/ui/dragDrop.ts`
- entrypoint and Vite types: `src/main.tsx`、`src/vite-env.d.ts`
- tests: `crates/core/tests/task_service_sqlite_tests.rs`、
  `src-tauri/src/lib.rs` の command/handler tests、
  `tests/adapters/tauriTaskRepository.test.ts`、`tests/ui/App.test.tsx`、
  `tests/ui/dragDrop.test.ts`

GitHub連携、CLI、設定ページ、公開URL、PR preview URL、
キーボードDnD完成対応、モバイル / タッチDnD最適化は実装していない。
これらはv2以降の判断対象としてrequirements側のfuture scopeに残す。
