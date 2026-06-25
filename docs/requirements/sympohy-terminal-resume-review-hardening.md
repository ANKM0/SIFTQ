---
codd:
  node_id: req:sympohy-terminal-resume-review-hardening
  type: requirement
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
---

# sympohy Terminal Resume and Review Failure Hardening Requirements

## 背景

`sympohy` は issue-driven automation の実行状態を GitHub issue label、
local state、PR metadata、review result から再構成する。運用上は、completed
issue の resume、stale local state の整合、PR mergeability の確認、review
loop の失敗通知、automation-created PR の traceability を壊さずに扱う必要がある。

## 概要

この要求仕様は、terminal resume と review-loop failure handling を
hardening するための外部振る舞いを定義する。

## 機能要件

- `task ai:sympohy:resume -- '#<issue>'` で completed issue を再開した場合、
  terminal state は `sympohy:blocked` / stale phase に戻さず、
  `sympohy:done` と `sympohy:phase:finalize` を保持または復元する。
- local の `state.json` が `blocked` を示していても、GitHub issue が completed
  なら completed terminal state として reconcile する。
- `main` と conflict している PR は、adversarial review / fix loop に入る前に
  dedicated mergeability gate で block する。
- mergeability block comment には、PR number、base/head、conflict summary、
  recommended action を含める。
- review loop が上限に到達して block される場合、block comment には最後に残った
  blocking findings の summary を含める。
- automation-created PR は issue traceability、summary、validation 欄を持つ。
- 既存 PR body が空の場合は、template 回復ではなく explicit block として扱う。

## 非機能要件

- terminal state の reconcile と block comment は idempotent であること。
- block comment は operator と automation の両方にとって十分に具体的であること。
- review loop の上限処理は、最後に失敗した理由を run log だけに閉じ込めず
  issue comment から追跡できること。

## 関連Issue

- #116

## 未決事項

現時点ではなし。
