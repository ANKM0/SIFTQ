---
codd:
  node_id: req:matrix-mvp-non-functional
  type: requirement
  status: draft
  depends_on:
    - id: req:yoriwake-system
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

v1 MVPでは、マトリックス操作を評価しやすくしながら、計画中のローカル
アプリケーション構成へ進める余地を残す。

## Requirements

- ドラッグアンドドロップは、コア操作の良し悪しを判断できる程度に
  応答性があること。
- マトリックスレイアウトは、各象限への配置意図を理解しやすいこと。
- 実装では、UI、アプリケーションの振る舞い、データアクセスの責務を
  分離すること。
- v1実装では、永続化、GitHub同期、Tauri commandsへの強い依存を避ける
  こと。
- タスク操作は、小さなapplication functionsまたはinterfacesとして表現し、
  後から実装先を差し替えられること。
- v1 frontendは、後続マイルストーンでTauri shellへ移植できること。
- 技術選定では、MVPで必要になるまで不要なライブラリを追加しないこと。

## Architectural Constraints

v1 MVPはマトリックスUIに対して高凝集でありつつ、将来のinfrastructureとは
疎結合である必要がある。具体的には次を満たす。

- Matrix componentsは表示と操作状態を担当する。
- Domain typesはReactに依存せず、タスクと象限を表現する。
- データアクセスはtask repository interfaceの背後に隠す。
- 最初のrepository実装はin-memoryのみでよい。
- 将来のrepository実装は、Rust、SQLite、GitHub同期を背後に持つ
  Tauri commandsを呼び出してよい。
