---
codd:
  node_id: req:matrix-mvp-functional
  type: requirement
  status: implemented
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: product
  depended_by:
    - id: req:matrix-mvp-non-functional
      relation: depends_on
      semantic: quality
    - id: req:matrix-mvp-v2-browser-storage
      relation: depends_on
      semantic: product
    - id: req:task-list-v3
      relation: depends_on
      semantic: product
    - id: design:matrix-mvp-technology-selection
      relation: depends_on
      semantic: product
    - id: design:browser-spa-v1-matrix-mvp-adr
      relation: depends_on
      semantic: scope
    - id: design:browser-only-matrix-runtime-storage-adr
      relation: depends_on
      semantic: target-architecture
    - id: design:react-typescript-vite-matrix-ui-adr
      relation: depends_on
      semantic: ui
    - id: design:frontend-port-adapter-boundary-adr
      relation: depends_on
      semantic: architecture
    - id: design:dnd-kit-matrix-drag-and-drop-adr
      relation: depends_on
      semantic: interaction
    - id: design:matrix-mvp-wireframe
      relation: depends_on
      semantic: ui
    - id: design:matrix-mvp-wireframe-layout-adr
      relation: depends_on
      semantic: scope
    - id: design:task-list-v3-wireframe
      relation: depends_on
      semantic: ui
---

# Matrix MVP Functional Requirements

## Purpose

Matrix MVPでは、アイゼンハワーマトリックスを中心にした2次元タスク配置UIが、
タスク作成、表示、並び替え、ドラッグアンドドロップ操作、ブラウザ上の永続化に
対して十分に自然な体験を提供できるかを検証する。

## Scope

areaは4つのmatrix areaと、補助area 2つの合計6つを持つ。

- Do
- Schedule
- Delegate
- Eliminate
- Skipped
- Done

ユーザーはこのページ上でタスクを作成し、作成したタスクをカードとして確認し、
ドラッグアンドドロップでmatrix area内の並び替え、matrix area間の移動、
DoneまたはSkippedへのステータス更新を行える必要がある。

## Functional Requirements

- マトリックスページは4つのmatrix areaを2x2レイアウトで表示する。
- Skipped areaは2x2マトリックスの左側にドロップareaとして表示する。
- Done areaは2x2マトリックスの右側にドロップareaとして表示する。
- ユーザーは各matrix areaの `+` からタイトルを指定してタスクを作成できる。
- 新規作成されたタスクは、対象matrix areaの一番下にカードとして表示される。
- ユーザーはタスクカードを同じmatrix area内でドラッグして並び替えできる。
- ユーザーはタスクカードを別のmatrix areaへドラッグして移動できる。
- 並び替え後、またはmatrix area間移動後の順番はbrowser storageに保持する。
- DoneまたはSkippedへのドロップはステータス更新として扱う。
- DoneまたはSkippedへ移動したタスクは通常表示からは見えなくする。
- Browser reload後も、task title、area、status、orderを復元できる。
- `task frontend:dev` でローカルブラウザからMVPを確認できる。
- `task ci:build` で静的SPAとしてビルドできる。

## Task Card Requirements

タスクカードは次の必須情報を持つ。

- `id`: タスクを一意に識別する内部ID。
- `title`: ユーザーが入力するタスク名。
- `areaId`: 現在所属しているarea。
- `status`: `active`、`done`、`skipped` のいずれか。
- `order`: area内の表示順。

`title` は次を満たす。

- trim後空は不可とする。
- 1文字以上、256文字以下とする。
- 重複を許可する。
- 自動切り詰めはしない。

## Acceptance and Verification

手動確認では少なくとも次を確認する。

- 4つのmatrix area、Done area、Skipped areaが表示される。
- 各matrix areaの `+` からタスクを作成できる。
- タスクカードをmatrix area内で並び替えできる。
- タスクカードを別のmatrix areaへ移動できる。
- Done / Skippedへドロップするとカードが通常表示から見えなくなる。
- Browser reload後も task title、area、status、order が復元される。
- 長いtitleでもレイアウトが崩れない。

## Implementation Traceability

- `src/contracts/task.ts`: frontend task contract、area、status。
- `src/domain/taskRules.ts`: area、title制約、status、matrix表示可否、area順。
- `src/ports/taskRepository.ts`: UIとadapterを分離するtask repository port。
- `src/adapters/browserTaskRepository.ts`: browser storage adapter。
- `src/ui/App.tsx`: Matrix page、area別作成フォーム、カード表示、DnD接続。
- `src/ui/dragDrop.ts`: dnd-kitのdrop id解決、move/reorder operation変換。

自動テスト証跡は次の通り。

- `tests/adapters/browserTaskRepository.test.ts`: browser storage persistence、
  title正規化、order正規化、storage error handling。
- `tests/ui/App.test.tsx`: area表示、作成フォーム、カード表示、area別表示更新、
  browser reload復元。
- `tests/ui/dragDrop.test.ts`: DnD drop解決、invalid drop、drag操作範囲制限。

## Out of Scope

- Done / Skippedの一覧表示。
- Done / Skippedからの復元。
- 複数端末同期。
- GitHub Issues / Projects連携。
- CLI利用。
- Rust backend commands。
- Tauriによるデスクトップアプリ化。
- SQLite永続化。
- 認証とトークン管理。
- 設定ページ。
- キーボードDnDの完成対応。
- モバイル / タッチDnD最適化。
- 公開URL。
- PR preview URL。
- `description`。
- `createdAt` / `updatedAt` のUI表示。

## Future Scope

後続では、CLI、GitHub同期、設定ページ、公開URL、PR preview URL、
キーボードDnD、モバイル / タッチDnD最適化、IndexedDB / OPFS などのstorage移行を
追加する可能性がある。frontendは、マトリックスUIを書き直さずにそれらを追加
できる境界を保つ。
