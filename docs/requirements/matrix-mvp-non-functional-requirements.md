---
codd:
  node_id: req:matrix-mvp-non-functional
  type: requirement
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: product
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: quality
  depended_by:
    - id: design:issue-6-matrix-mvp-tech-selection
      relation: depends_on
      semantic: product
    - id: design:browser-spa-v1-matrix-mvp-adr
      relation: depends_on
      semantic: scope
    - id: design:rust-tauri-v2-local-application-adr
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

v1 MVPでは、アイゼンハワーマトリックス上のタスク配置、area内並び替え、
area間移動、Done / Skippedへのステータス更新を評価しやすくしながら、
計画中のローカルアプリケーション構成へ進める余地を残す。

## Requirements

- ドラッグアンドドロップは、コア操作の良し悪しを判断できる程度に応答性が
  あること。
- v1必須のDnDは、デスクトップブラウザのポインター操作とする。
- キーボードDnDはv1必須にしない。
- モバイル / タッチDnD最適化はv1必須にしない。
- キーボードDnDとモバイル / タッチDnDは、後から拡張できるようにする。
- マトリックスレイアウトは、各matrix areaへの配置意図を理解しやすいこと。
- Done / Skippedは、2x2マトリックス外側のステータス更新用ドロップareaとして
  理解しやすいこと。
- 実装では、UI、アプリケーションの振る舞い、データアクセスの責務を
  分離すること。
- v1実装では、永続化、GitHub同期、Tauri commandsへの強い依存を避ける
  こと。
- タスク操作は、小さなapplication functionsまたはinterfacesとして表現し、
  後から実装先を差し替えられること。
- task作成、matrix area間移動、matrix area内並び替え、Done / Skippedへの
  ステータス更新はapplication operationとして表現すること。
- dnd-kit依存はUI interaction layerに閉じること。
- domain、application、repositoryへdnd-kit固有概念を漏らさないこと。
- v1 frontendは、後続マイルストーンでTauri shellへ移植できること。
- 技術選定では、MVPで必要になるまで不要なライブラリを追加しないこと。
- MVP完了判定には自動テストだけでなく、操作感の手動確認も含めること。
- 手動確認結果と既知制約は、PRまたは該当issueに記録すること。
- 公開URLとPR preview URLはv1必須にしないこと。

## Architectural Constraints

v1 MVPはマトリックスUIに対して高凝集でありつつ、将来のinfrastructureとは
疎結合である必要がある。具体的には次を満たす。

- Matrix componentsは表示と操作状態を担当する。
- Domain typesはReactに依存せず、task、area、status、orderingを表現する。
- Domainは疎結合・高凝集に分ける。
- Task、Area、Status、orderingなどの責務を1つの巨大な型や神クラスに
  集約しない。
- Domain modelはReact、dnd-kit、repository実装に依存しない。
- Application operationは小さく保ち、task作成、area間移動、area内並び替え、
  status更新を分けて表現する。
- UI固有のイベントや表示都合をdomainへ漏らさない。
- データアクセスはtask repository interfaceの背後に隠す。
- 最初のrepository実装はin-memoryのみでよい。
- 将来のrepository実装は、Rust、SQLite、GitHub同期を背後に持つ
  Tauri commandsを呼び出してよい。
