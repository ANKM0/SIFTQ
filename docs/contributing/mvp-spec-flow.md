---
codd:
  node_id: design:mvp-spec-flow
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
---

# MVP Spec Flow

SIFTQ の MVP 開発では、LLM に実装を依頼する前に、要件、設計、
必要な wireframe、テスト観点を最小限の文書でそろえる。要件から
実装へ直接飛ばず、外部から観測できる振る舞いと UI 契約を先に
固定することで、実装イメージのぶれを減らす。

## CoDD Traceability

この文書の CoDD node は `design:mvp-spec-flow` とする。
SIFTQ の system requirement anchor である `req:siftq-system` に依存し、
依存関係の semantic は `governance` とする。

## 最小フロー

基本フローは次の順序とする。

```text
Requirements -> Design -> Wireframe（UI 変更時） -> ADR Decision -> Implementation Request
```

必須文書は原則として次の 2 つにする。

- `docs/requirements/<feature>.md`
- `docs/design/<feature>.md`

UI 変更がある場合は、追加で次の wireframe 文書と wireframe HTML
更新を必須にする。

- `docs/wireframes/<feature>.md`
- `docs/wireframes/<feature>.html` または既存 wireframe HTML

Refinement は独立した文書にしない。未決事項、対象範囲、受け入れ
条件の整理は requirements 作成プロセスの一部として扱う。

## Requirements Template

Requirements は「何を満たすべきか」を記録する。機能の目的、対象範囲、
対象外、機能要件、受け入れ条件を先に明確にし、設計や実装の判断を
要求として混ぜない。

`docs/requirements/<feature>.md` は次の最小テンプレートで作成する。
各節は空のまま残さず、未確定の内容は `Open Questions（未決事項）` に
集約する。

```md
# <Feature> Requirements

## Purpose（目的）

## Scope（対象範囲）

## Out of Scope（対象外）

## Functional Requirements（機能要件）

## Acceptance Criteria（受け入れ条件）

## Open Questions（未決事項）
```

性能、アクセシビリティ、運用、セキュリティなど、機能要件だけでは
判断できない制約がある場合だけ、次の節を追加する。

```md
## Non-Functional Requirements（非機能要件）
```

## Design Template

Design docs は「この機能をどう作るか」を記録する。個別機能の外部設計、
内部設計、テスト観点、UI 状態、operation / port / adapter の追加内容、
ADR で決まった判断をその機能へどう適用するかを書く。

`External Design（外部設計）` は UI 限定ではない。ユーザー、テスト、
外部モジュールから観測できる振る舞いを書く。

`docs/design/<feature>.md` は次の最小テンプレートで作成する。
各節は implementation request に進める粒度まで具体化し、未確定の内容は
`Open Questions（未決事項）` に集約する。

```md
# <Feature> Design

## External Design（外部設計）

## Internal Design（内部設計）

## Test Viewpoints（テスト観点）

## Open Questions（未決事項）
```

Design docs は ADR の判断を再決定してはならない。既存 ADR を参照し、
その判断を個別機能の設計へどう適用するかだけを記録する。

## Wireframe Markdown Template

Wireframe は外部設計の一部として扱う。UI 変更がある機能では、
Markdown で UI 契約を記録し、HTML wireframe で表示状態を確認できる
ようにする。

wireframe CoDD node の命名規則は `design:<feature-wireframe>` とする。
UI 契約は機能 design 本体とは別の design node として扱い、機能 design
本体の `design:<feature>` と混在させない。

```text
design:<feature>
design:<feature-wireframe>
```

`design:<feature-wireframe>` の CoDD node は
`docs/wireframes/<feature>.md` に置く。

`docs/wireframes/<feature>.md` は次の最小テンプレートで作成する。
Markdown では画面の実装方法ではなく、HTML wireframe が満たすべき
外部契約を記録する。各節は空のまま残さず、未確定の内容は
`Open Questions（未決事項）` に集約する。

```md
---
codd:
  node_id: design:<feature-wireframe>
  type: design
  status: draft
  depends_on:
    - id: design:<feature>
      relation: depends_on
      semantic: ui
---

# <Feature> Wireframe

## Target HTML（対象HTML）

対象の HTML wireframe ファイル、または更新する既存 HTML wireframe を
列挙する。

## UI Contract（UI契約）

ユーザーやテストから観測できる領域、操作、表示ルールを記録する。

## States（状態）

通常、空、入力中、検証エラー、成功、失敗など、HTML wireframe で
確認する状態を記録する。

## Copy and Layout（文言とレイアウト）

表示文言、主要な配置、表示順、表示しない情報を記録する。

## Contract Test（契約テスト）

`tests/docs/wireframeContract.test.ts` で固定する契約と、更新不要と
判断した契約を記録する。

## Open Questions（未決事項）
```

UI 変更 PR では、文言修正や小さいスタイル調整でも wireframe HTML を
更新する。`tests/docs/wireframeContract.test.ts` は UI 変更 PR で必ず
確認する。新しい UI 状態、操作、表示契約が増える場合だけ、この契約
テストの更新を必須にする。

## ADR Decision

ADR は、なぜこの基盤、方針、技術を選ぶかを記録する。複数機能に
影響する判断、または後から変更コストが高い durable decision に使う。

### ADR / Design Doc Boundary

ADR と design doc の境界は、判断の寿命と適用範囲で分ける。

- ADR は durable decision を記録する。採用した基盤、方針、技術、
  architecture boundary、repository workflow と、その判断理由を残す。
- Design doc は feature-specific application を記録する。per-feature
  external design、internal design、test perspectives、既存 ADR の
  application を対象機能ごとに残す。あわせて UI 状態と operation flow
  を残す。
- Design doc は ADR の判断を再決定してはならない。ADR と異なる判断が
  必要になった場合は、design doc に判断を埋め込まず、新しい ADR または
  既存 ADR の改訂で扱う。
- ADR は feature-specific implementation details を持たない。個別画面の
  文言、イベントフロー、operation 呼び出し、テストケースは design doc
  に置く。

次のどちらかに該当する場合は、ADR を作成する。

- 判断が複数機能、複数ドキュメント、または repository workflow に
  影響する。
- 判断を後から変えると migration、schema 変更、toolchain 移行、
  runtime 変更、storage 移行、または architecture boundary の変更が
  必要になる。

ADR が必要になる代表例:

- アーキテクチャ判断
- 主要モジュール
- ライブラリ
- ツール
- runtime
- storage
- schema
- migration
- toolchain
- governance
- architecture boundary

例として、React + Vite、dnd-kit、Rust/Tauri、SQLite、
port-adapter boundary、pnpm、Taskfile、GitHub Actions のような判断は
ADR で扱う。

実装依頼へ進む前に、次のどちらかを design doc に明記する。

- 既存 ADR を使う場合: 参照する ADR と、その判断をこの機能へどう
  適用するか。
- 新しい ADR が必要な場合: `docs/adr/` に ADR を追加し、ADR が
  Accepted になってから implementation request へ進むこと。

ADR が不要な場合は、不要と判断した理由を design doc の Open Questions
または decision note に残す。たとえば既存の module boundary、runtime、
storage、toolchain を変えず、機能固有の UI / operation / test だけで
閉じる変更は ADR なしで進める。

Design docs は、その基盤や方針を使って、この機能をどう作るかを
記録する。たとえば title edit 機能では、card 内の Edit から modal を
開く、Save は `updateTaskTitle` を呼ぶ、create と同じ title validation
を使う、どのテストで何を確認するかを書く。

ADR は durable decision、design docs は feature-specific application
を扱う。design docs は ADR の判断を再決定してはならない。
