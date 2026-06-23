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
    - id: design:browser-only-matrix-runtime-storage-adr
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
現在の優先要件は、要素移動が滑らかなマトリックスUIをブラウザで使え、
自分のPCでもインストールなしに継続利用できることである。

CLI、native app shell、GitHub連携は追加コンテンツとして後続issueで扱う。

## 採用方針

Matrix MVPは browser-only runtime として実装する。UI基盤はReact、
TypeScript、Vite、dnd-kitを継続し、保存先は `TaskRepository` port の背後に
置くbrowser storage adapterとする。

## 技術選定

| 領域 | 選定 | 時期 |
| --- | --- | --- |
| application形態 | Browser SPA | MVP |
| UI基盤 | React, TypeScript, Vite | MVP |
| drag and drop | dnd-kit | MVP |
| data境界 | browser storage adapterを持つTask repository port | v2 MVP |
| 永続化 | browser storage | v2 MVP |
| CLI | 後続判断 | v2以降 |
| GitHub連携 | 後続判断 | v2以降 |
| native app shell | 後続判断 | v2以降 |

## 言語・フレームワーク選定

| 領域 | 選定 | 理由 |
| --- | --- | --- |
| UI言語 | TypeScript | task、area、repository interfaceの境界を型で表現するため。 |
| UI framework | React | matrix page、area、task card、task creation formをcomponent単位で分離しやすいため。 |
| build tool | Vite | SPAのfeedback loopが速く、静的bundleとして配布しやすいため。 |
| DnD framework | dnd-kit | React上でtask cardのdrag and dropを実装しやすく、DnD logicをUI interaction layerに閉じ込めやすいため。 |
| storage adapter | TypeScript browser storage | ブラウザのみで使え、Matrix操作規模では十分な応答性を維持できるため。 |

Rust、Tauri、SQLiteは #59 の必須依存にしない。滑らかな要素移動はbackend言語では
なく、React再描画量、dnd-kitの使い方、CSS transform、DOM数で決まるためである。

## 実装指針

frontendでは、contract、domain rules、repository port、storage adapter、UI
componentを分ける。代表的な配置は次の通り。

```text
contracts/
domain/
ports/
adapters/
ui/
```

本番repositoryはbrowser storage adapterとする。後続のstorageは、同じ
frontend interfaceを維持したままIndexedDB、OPFS、remote API、GitHub同期などへ
差し替えられる。

## 完了トレーサビリティ

現在の完了範囲は次の実装単位に対応する。

- frontend contract and adapter boundary: `src/contracts/task.ts`、
  `src/domain/taskRules.ts`、`src/ports/taskRepository.ts`、
  `src/adapters/browserTaskRepository.ts`
- UI and interaction layer: `src/ui/App.tsx`、`src/ui/App.css`、
  `src/ui/taskPresentation.ts`、`src/ui/dragDrop.ts`
- entrypoint and Vite types: `src/main.tsx`、`src/vite-env.d.ts`
- tests: `tests/adapters/browserTaskRepository.test.ts`、`tests/ui/App.test.tsx`、
  `tests/ui/dragDrop.test.ts`

GitHub連携、CLI、設定ページ、公開URL、PR preview URL、
キーボードDnD完成対応、モバイル / タッチDnD最適化は実装していない。
これらは後続判断対象としてrequirements側のfuture scopeに残す。
