---
codd:
  node_id: req:sympohy-llm-loop-observability-self-improvement
  type: requirement
  status: draft
  depends_on:
    - id: req:repository-governance
      relation: depends_on
      semantic: governance
  depended_by:
    - id: design:sympohy-llm-loop-observability-self-improvement
      relation: depends_on
      semantic: requirement
---

# sympohy LLM Loop Observability and Self-Improvement Requirements

## 背景

`sympohy` は issue-driven automation の実行状態を local state、logs、GitHub
labels、PR metadata、review result から復元する。Issue #126 では、実行中の
LLM loop を監査・分析できる観測基盤と、そこから安全に改善候補を出す
self-improvement workflow を追加する必要がある。

この要求仕様は、resume 用の state と監査用の event stream を分離し、観測
データを replay 可能に保ったまま、低リスクな改善提案と検証済み draft PR 生成
までを定義する。

## 概要

この要求仕様は、sympohy の観測イベント、集計用 store、failure taxonomy、
proposer / applicator workflow、そして秘匿情報と大きな raw artifact を保存しない
運用制約を定義する。

## 機能要件

- `.sympohy/runs/issue-<number>/state.json` は resume 用の最新状態として維持し、
  append-only event stream を監査・分析用の一次記録として追加する。
- event stream は run ごとに追記専用で、replay から SQLite observation store を
  再構築できる。
- event schema は少なくとも `run_id`、`event_id`、`issue`、`phase`、`event type`、
  `status`、`attempt`、`duration`、`summary`、軽量 `metadata` を持つ。
- hook、command、Codex、stage gate、review、recovery、browser observation の主要
  境界で event を記録する。
- Codex 呼び出しは role、model、reasoning effort、prompt hash、parse status、
  duration、returncode または failure summary を記録する。
- test result summarizer は `pytest`、`vitest`、`task ci` の失敗 test 名、file、
  line、短い failure summary を best-effort で抽出する。
- browser observation は console error count、page error count、storage key count、
  state hash、accessibility summary などの軽量値を保存し、raw screenshot、
  Playwright trace、DOM dump を常時保存しない。
- developer instructions は raw copy ではなく source kind、path/ref、sha256、
  短い summary として保存する。
- failure taxonomy を定義し、blocked の最終原因だけでなく blocked までの event
  chain に failure kind / failure signature を付与できる。
- analyzer は failure kind 別件数、phase 滞留、retry 後に解決した failure、
  blocked した failure、recurring event chain pattern を集計できる。
- proposer は analyzer 結果と軽量 event chain summary から、prompt、hook、stage
  gate、docs、skill、test、config の改善候補 JSON を出せる。
- self-improvement applicator は low risk な docs、prompt、test fixture などに
  限定し、検証済み draft PR までで止まる。
- replay fixture または equivalent regression test により、taxonomy、analyzer、
  proposer schema の互換性が検証される。

## 非機能要件

- 観測DBと event stream は secret、private config、巨大 raw artifact を保存しない。
- replay と集計は deterministic で、同じ event stream から同じ store を再構築
  できること。
- 既存の resume、stale recovery、review、final verifier の挙動を変えないこと。
- low risk 変更以外の自動適用は行わず、dangerous な変更は人間レビューなしで
  確定しないこと。

## 関連Issue

- #126

## 保存形式

- event stream の保存形式は line-delimited JSON (`*.jsonl`) を採用する。
- record は append-only で追記し、各行が独立した event object になること。
- record には `run_id` を必須で含め、同一 issue 配下で複数 run が混在しても replay
  側で分離できること。
