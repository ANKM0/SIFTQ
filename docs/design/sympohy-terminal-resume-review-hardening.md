---
codd:
  node_id: design:sympohy-terminal-resume-review-hardening
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:sympohy-issue-execution
      relation: depends_on
      semantic: automation
    - id: design:sympohy-run-lifecycle-state
      relation: depends_on
      semantic: lifecycle
    - id: design:sympohy-stale-run-recovery
      relation: depends_on
      semantic: recovery
---

# sympohy Terminal Resume and Review Failure Hardening Design

## External Design（外部設計）

- `task ai:sympohy:resume -- '#<issue>'` は completed issue を再開する場合でも、
  completed terminal state を維持する。
- local `state.json` が `blocked` を示していても、GitHub issue が completed なら
  resume path は `sympohy:done` と `sympohy:phase:finalize` を優先する。
- PR が `main` と conflict している場合、`sympohy` は adversarial review /
  fix loop の前に dedicated mergeability gate を実行し、1 回だけ pre-review
  auto-merge / auto-fix を試行する。
- mergeability block comment は PR number、base/head、conflict summary、
  recommended action を含む。
- review loop の上限に達した block comment は、最後に残った blocking findings の
  summary を含む。
- automation-created PR body は issue traceability、summary、validation を含む。
- 既存 PR body が空、または required metadata が不足している場合、`sympohy` は
  review 継続前に minimum metadata を backfill する。

## Internal Design（内部設計）

### Terminal resume reconciliation

resume path は、local state の phase/status だけで再開点を決めない。まず
GitHub issue の terminal state を確認し、completed issue なら local state が
`blocked` でも completed terminal state に正規化する。

この正規化では、issue label と local `state.json` の不整合を解消し、
`sympohy:done` と `sympohy:phase:finalize` を再付与する。resume 処理はこの状態を
新しい failure と見なさず、review loop や hook fix へ戻さない。

### Dedicated mergeability gate

review phase の前に、PR の mergeability を base branch との conflict 観点で
専用に判定する。ここで conflict が見つかった場合、まず base branch を取り込む
merge を 1 回だけ自動実行する。merge conflict が発生した場合は、Codex fix role
で conflict 解消を試行し、conflict marker が残っていないことを確認してから
`task ci` と push まで進める。

この pre-review auto-fix が失敗した場合だけ、adversarial review に進まず
issue を block する。block comment は構造化された metadata を含める。
最低限、PR number、base/head、conflict summary、recommended action を
renderer から渡し、comment builder が文章化する。

### Review-loop exhaustion handling

review loop が round limit に達した場合、最後に得られた blocking findings を
要約して block comment に載せる。要約は、最後の reviewer response から
critical/high/medium の残存理由を抽出し、operator が次の修正判断をできる粒度に
絞る。

blocking findings の詳細は run log と JSON artifact 側に保持し、issue comment は
人間がすぐ読める summary に限定する。

### PR metadata handling

automation-created PR は、issue traceability、summary、validation の各欄を
必須 metadata として埋める。body renderer は template をベースに生成し、
draft PR 作成時は full template を使う。

空の既存 PR body や required metadata 欠落を検出した場合は、issue 番号と
template から minimum metadata を backfill して `gh pr edit` で補完する。
既存の本文がある場合は、既存内容を保持しつつ不足 section だけを追記または
先頭に補う。

## Test Viewpoints（テスト観点）

- `tests/sympohy/sympohy_runner_test.py`
  - completed issue resume が `done/finalize` を保持または復元すること。
  - stale `state.json` の `blocked` が GitHub completed state により上書きされること。
  - mergeability conflict が review loop の前に 1 回だけ auto-fix を試みること。
  - pre-review mergeability auto-fix が base merge、Codex conflict fix、
    conflict-marker check、`task ci`、push を経由すること。
  - mergeability block comment に PR number、base/head、conflict summary、
    recommended action が入ること。
  - review loop 上限の block comment に最後の blocking findings summary が入ること。
  - empty PR body と metadata 不足 PR body が minimum metadata で backfill されること。
- `tests/sympohy/sympohyWorkflowContracts.test.ts`
  - PR metadata contract、mergeability gate の block comment 文言、resume terminal
    reconciliation の string-level contract を保持すること。

## ADR Application（ADR 適用）

新しい ADR は不要である。これは既存の sympohy automation、issue lifecycle、
review / merge workflow の範囲内の hardening であり、module boundary、
storage format、toolchain、repository workflow の durable decision を変更しない。

## Open Questions（未決事項）

現時点ではなし。
