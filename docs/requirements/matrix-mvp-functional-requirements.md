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
    - id: design:matrix-mvp-wireframe
      relation: depends_on
      semantic: ui
    - id: design:matrix-mvp-wireframe-layout-adr
      relation: depends_on
      semantic: scope
---

# Matrix MVP Functional Requirements

## Purpose

v1 MVPでは、アイゼンハワーマトリックスを中心にした2次元タスク配置UIが、
タスク作成、表示、並び替え、ドラッグアンドドロップ操作に対して十分に
自然な体験を提供できるかを検証する。これはUI検証のマイルストーンであり、
最終的なローカルアプリケーション構成を実装する段階ではない。

## Scope

v1 MVPでは、タスクを配置・遷移できる領域をareaと呼ぶ。areaは
アイゼンハワーマトリックスの4つのmatrix areaと、補助area 2つの合計6つを
持つ。

Matrix areaは次の4つとし、2x2マトリックスとして表示する。

- 重要かつ緊急: Do
- 重要だが緊急ではない: Schedule
- 重要ではないが緊急: Delegate
- 重要でも緊急でもない: Eliminate

補助areaは次の2つとし、2x2マトリックスの外側に長方形のドロップarea
として表示する。

- 行わない / 論理削除: Skipped。2x2マトリックスの左側に配置する。
- 完了: Done。2x2マトリックスの右側に配置する。

ユーザーはこのページ上でタスクを作成し、作成したタスクをカードとして
確認し、ドラッグアンドドロップでmatrix area内の並び替え、matrix area間の
移動、DoneまたはSkippedへのステータス更新を行える必要がある。

## Functional Requirements

- マトリックスページは4つのmatrix areaを2x2レイアウトで表示する。
- Skipped areaは2x2マトリックスの左側に長方形のドロップareaとして表示する。
- Done areaは2x2マトリックスの右側に長方形のドロップareaとして表示する。
- area labelは初期値を使う。
- 将来的には設定ページからarea labelを変更できる想定とする。
- v1では設定ページを作成しない。
- ユーザーは各matrix areaの `+` からタイトルを指定してタスクを作成できる。
- 新規作成されたタスクは、対象matrix areaの一番下にカードとして表示される。
- matrix area内の初期表示順は作成順にする。
- ユーザーはタスクカードを同じmatrix area内でドラッグして並び替えできる。
- ユーザーはタスクカードを別のmatrix areaへドラッグして移動できる。
- 並び替え後、またはmatrix area間移動後の順番は現在のブラウザセッション中
  保持する。
- DoneまたはSkippedへのドロップは並び替えではなくステータス更新として扱う。
- Doneへドロップされたタスクはstatusをdoneへ更新する。
- Skippedへドロップされたタスクはstatusをskippedへ更新する。
- DoneまたはSkippedへ移動したタスクは、v1の通常表示からは見えなくする。
- UIは現在のブラウザセッション中だけ、タスクと並び順をメモリ上に保持できる。
- `task frontend:dev` でローカルブラウザからMVPを確認できる。
- `task ci:build` で静的SPAとしてビルドできる。

## Task Card Requirements

v1 MVPのタスクカードは、次の必須情報を持つ。

- `id`: タスクを一意に識別する内部ID。titleでは識別しない。
- `title`: ユーザーが入力するタスク名。
- `areaId`: 現在所属しているarea。matrix area、Done、Skippedのいずれか。
- `status`: タスクの状態。matrix area上のタスクはactive、Doneへドロップすると
  done、Skippedへドロップするとskippedにする。
- `order`: area内の表示順。matrix area内の作成順、並び替え順を保持する。

`title` は次を満たす。

- 1文字以上、256文字以下とする。
- trim後空は不可とする。
- 重複を許可する。
- 256文字超過は作成不可とする。
- 自動切り詰めはしない。

v1 MVPでは、次の情報はタスクカードの必須要素にしない。

- `description`
- `dueDate`
- `assignee`
- `labels` / `tags`
- `priority`
- `createdAt`
- `updatedAt`
- `completedAt`
- `skippedAt`
- `githubIssueId`

カード上に必ず表示するのは `title` とする。`id`、`areaId`、`status`、
`order` は内部状態として保持し、カード上に表示しなくてよい。長いtitleでも
カードやareaのレイアウトを崩さない。

## Task Creation Requirements

- trim後に空の間は作成ボタンをdisabledにする。
- 何らかの理由で作成処理が走り、trim後に空だった場合はカードを作成せず、
  エラーを表示する。
- 重複タイトルは許可する。
- 重複警告は出さない。
- タスク識別はtitleではなくidで行う。
- titleは最大256文字にする。
- 256文字超過は作成不可にする。
- 自動切り詰めはしない。

## Acceptance and Verification

MVP完了判定には、自動チェックだけでなくローカルブラウザでの手動確認も
含める。手動確認では少なくとも次を確認する。

- 4つのmatrix area、Done area、Skipped areaが表示される。
- 各matrix areaの `+` からタスクを作成できる。
- 作成したタスクが対象matrix areaの一番下に追加される。
- タスクカードをmatrix area内で並び替えできる。
- タスクカードを別のmatrix areaへ移動できる。
- DnD後の順番が現在のブラウザセッション中保持される。
- Doneへドロップするとカードが通常表示から見えなくなる。
- Skippedへドロップするとカードが通常表示から見えなくなる。
- 長いtitleでもレイアウトが崩れない。

手動確認結果と既知制約は、PRまたは該当issueに記録する。

## Implementation Traceability

v1 MVPの実装証跡は次の通り。

- `src/domain/area.ts`: 4つのmatrix areaとDone / Skippedのarea定義。
- `src/domain/task.ts`: task title制約、status、matrix表示可否。
- `src/application/taskOperations.ts`: task作成、一覧、移動、並び替えoperation。
- `src/ports/taskRepository.ts`: UIとadapterを分離するtask repository port。
- `src/adapters/inMemoryTaskRepository.ts`: 現在のブラウザセッション中だけ保持する
  in-memory repository。
- `src/ui/App.tsx`: Matrix page、area別作成フォーム、カード表示、DnD接続。
- `src/ui/dragDrop.ts`: dnd-kitのdrop id解決、move/reorder operation変換、
  操作範囲制限。

自動テスト証跡は次の通り。

- `tests/domain/task.test.ts`: area定義、title正規化、status、表示可否。
- `tests/application/taskOperations.test.ts`: application operationの作成、
  入力拒否、重複title、移動、並び替え。
- `tests/adapters/inMemoryTaskRepository.test.ts`: order、status遷移、terminal
  area、in-memory repository振る舞い。
- `tests/ui/App.test.tsx`: area表示、作成フォーム、カード表示、セッション内保持、
  area別表示更新、長いtitle。
- `tests/ui/dragDrop.test.ts`: DnD drop解決、invalid drop、drag操作範囲制限。

## Out of Scope for v1

- Done / Skippedの一覧表示。
- Done / Skippedからの復元。
- GitHub Issues連携。
- GitHub Projects連携。
- CLI利用。
- Rust backend commands。
- Tauriによるデスクトップアプリ化。
- SQLiteまたはブラウザDBによる永続化。
- 認証とトークン管理。
- 設定ページ。
- キーボードDnDの完成対応。
- モバイル / タッチDnD最適化。
- 公開URL。
- PR preview URL。
- `description`。
- `dueDate`。
- `assignee`。
- `labels` / `tags`。
- `priority`。
- `createdAt` / `updatedAt` のUI表示。
- `completedAt` / `skippedAt`。
- `githubIssueId`。
- タスク一覧、その他の副次的なページ。

## Future Scope

v2 MVP以降では、RustとTauriによるローカルアプリケーション、GUIとCLIの
共通インターフェース、SQLiteによる永続化、GitHub同期、設定ページ、公開URL、
PR preview URL、キーボードDnD、モバイル / タッチDnD最適化を追加する可能性が
ある。v1 frontendは、マトリックスUIを書き直さずにそれらを追加できる境界を
保つ。
