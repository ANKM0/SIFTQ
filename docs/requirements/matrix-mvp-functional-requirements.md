---
codd:
  node_id: req:matrix-mvp-functional
  type: requirement
  status: draft
  depends_on:
    - id: req:yoriwake-system
      relation: depends_on
      semantic: product
  depended_by:
    - id: req:matrix-mvp-non-functional
      relation: depends_on
      semantic: quality
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

# Matrix MVP Functional Requirements

## Purpose

v1 MVPでは、2次元タスクマトリックスがタスク作成、表示、ドラッグ
アンドドロップ操作に対して十分に自然な体験を提供できるかを検証する。
これはUI検証のマイルストーンであり、最終的なローカルアプリケーション
構成を実装する段階ではない。

## Scope

v1 MVPでは、次の4象限を持つマトリックスページを1画面だけ提供する。

- Do
- Decide
- Delegate
- Delete

ユーザーはこのページ上でタスクを作成し、作成したタスクをカードとして
確認し、ドラッグアンドドロップで象限間を移動できる必要がある。

## Functional Requirements

- マトリックスページは4象限を2次元レイアウトで表示する。
- ユーザーはタイトルを指定してタスクを作成できる。
- 作成されたタスクは、いずれかの象限にカードとして表示される。
- ユーザーはタスクカードをある象限から別の象限へドラッグできる。
- ドロップ後、移動したタスクは移動先の象限に表示される。
- UIは現在のブラウザセッション中だけ、タスクをメモリ上に保持できる。

## Out of Scope for v1

- GitHub Issues連携。
- GitHub Projects連携。
- CLI利用。
- Rust backend commands。
- Tauriによるデスクトップアプリ化。
- SQLiteまたはブラウザDBによる永続化。
- 認証とトークン管理。
- タスク一覧、設定、その他の副次的なページ。

## Future Scope

v2 MVP以降では、RustとTauriによるローカルアプリケーション、GUIとCLIの
共通インターフェース、SQLiteによる永続化、GitHub同期を追加する可能性が
ある。v1 frontendは、マトリックスUIを書き直さずにそれらを追加できる
境界を保つ。
