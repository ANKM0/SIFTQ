---
codd:
  node_id: req:matrix-mvp-non-functional
  type: requirement
  status: implemented
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: product
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: quality
  depended_by:
    - id: design:matrix-mvp-technology-selection
      relation: depends_on
      semantic: product
    - id: req:matrix-mvp-v2-browser-storage
      relation: depends_on
      semantic: quality
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
---

# Matrix MVP Non-Functional Requirements

## Quality Goals

Matrix MVPでは、アイゼンハワーマトリックス上のタスク配置、area内並び替え、
area間移動、Done / Skippedへのステータス更新を評価しやすくしながら、
ブラウザのみで使える永続化を提供する。

## Requirements

- ドラッグアンドドロップは、コア操作の良し悪しを判断できる程度に応答性があること。
- 必須のDnDは、デスクトップブラウザのポインター操作とする。
- キーボードDnDは必須にしない。
- モバイル / タッチDnD最適化は必須にしない。
- UI、domain rules、データアクセスの責務を分離すること。
- GitHub同期、CLI、native app shellへの強い依存を避けること。
- task作成、matrix area間移動、matrix area内並び替え、Done / Skippedへの
  ステータス更新はrepository operationとして表現すること。
- dnd-kit依存はUI interaction layerに閉じること。
- domain rules、repositoryへdnd-kit固有概念を漏らさないこと。
- frontendは、後続マイルストーンでstorage adapterを差し替えられること。
- MVP完了判定には自動テストだけでなく、操作感とreload復元の手動確認も含めること。

## Architectural Constraints

- Matrix componentsは表示と操作状態を担当する。
- Domain rulesはReactに依存せず、task、area、status、orderingを表現する。
- UI固有のイベントや表示都合をdomain rulesへ漏らさない。
- データアクセスはtask repository interfaceの背後に隠す。
- repository実装はbrowser storageを使う。
- 将来のrepository実装は、IndexedDB、OPFS、remote API、GitHub同期などへ
  差し替えてよい。

## Verification Traceability

- DnD応答性と操作感は、`task frontend:dev` で起動したローカルブラウザ上の
  Matrix MVP smoke checkで確認する。
- DnD解決ロジックと画面外への過剰なdrag移動制限は `tests/ui/dragDrop.test.ts`
  で確認する。
- UI、domain rules、frontend repository port、browser storage adapterの責務分離は
  `src/ui/App.tsx`、`src/domain/taskRules.ts`、`src/ports/taskRepository.ts`、
  `src/adapters/browserTaskRepository.ts` の import境界と、それぞれに対応する
  テストで確認する。
- GitHub同期、CLI、native app shell、設定ページ、公開URL、PR preview URLを
  実装しないことは、READMEの手動確認範囲とrequirementsのscope分離で確認する。
- `task ci:typecheck`、`task ci:lint`、`task ci:test`、`task ci:build`、
  `task codd:scan`、`task codd:validate`、`task codd:dag` をMVP完了時の
  自動確認とする。
