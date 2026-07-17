---
codd:
  node_id: design:sympohy-llm-loop-observability-self-improvement
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
    - id: design:sympohy-terminal-resume-review-hardening
      relation: depends_on
      semantic: hardening
    - id: design:sympohy-llm-loop-observability-self-improvement-adr
      relation: depends_on
      semantic: decision
---

# sympohy LLM Loop Observability and Self-Improvement Design

## External Design（外部設計）

- `state.json` は resume 用の最新状態として残し、監査・分析は append-only event
  stream を正とする。
- event stream は run、issue、phase、event type、status、attempt、duration、
  summary、軽量 metadata を含む観測境界の共通記録になる。
- SQLite observation store は event stream の派生物として再構築可能であり、
  直接の一次記録にはしない。
- hook、command、Codex、stage gate、review、recovery、browser observation の各
  境界で event を残す。
- browser observation は軽量メトリクスのみを保存し、raw screenshot、trace、
  DOM dump は永続化しない。
- developer instructions は raw copy を保存せず、source kind、path/ref、sha256、
  summary に正規化して記録する。
- analyzer は failure kind 別件数、phase 滞留、retry 後に解決した failure、
  blocked した failure、recurring event chain pattern を返す。
- proposer は analyzer 結果と event chain summary から、prompt、hook、stage gate、
  docs、skill、test、config に対する改善候補 JSON を返す。
- applicator は docs、prompt、test fixture などの low risk 領域に限定し、修正済み
  draft PR の作成までで止まる。

## Internal Design（内部設計）

### Current path inventory

logical step 1 では、まず既存の実行経路ごとの永続化ポイントを棚卸しし、どの記録を
resume 用 state に残し、どの記録を event stream へ移すかを固定する。

- `scripts/sympohy/runner.py:_RunStateWriter`
  - `.sympohy/runs/issue-<number>/state.json` に run ごとの最新 phase、status、
    pid、heartbeat、lock、branch、worktree、plan reference、last progress を上書き
    保存する。
  - `record_recovery()` は `last_recovery` を state に反映しつつ、
    `.sympohy/runs/issue-<number>/recovery.log` へ recovery event を append する。
- `scripts/sympohy/core.py:inspect_running_issue`
  - resume / stale 判定は `state.json` の phase、pid、heartbeat を優先し、欠損時だけ
    GitHub label を fallback に使う。
- `scripts/sympohy/stage_gate.py:evaluate_stage`
  - stage gate 自体は stateless に評価し、runner から渡された context と stage
    result JSON を境界にしている。
- review / final verifier / fix loop
  - `review-<n>.json`、`final-verifier-<n>.json`、`final-verifier.json`、
    `final-verifier-fix-<n>.log` などの point artifact はあるが、phase 横断で共通の
    append-only audit trail は未定義である。
- resume 経路
  - `resume_issue()` と late-phase handler は `state.json` と point artifact を読み、
    `state.json` を更新しながら再開点を決める。resume 自体の判断根拠を横断的に
    replay できる stream はまだ無い。

### Event stream

各 run は append-only な event stream を持つ。event は replay 可能であることを
優先し、以下の共通フィールドを持つ。

- `run_id`
- `event_id`
- `issue`
- `phase`
- `event_type`
- `status`
- `attempt`
- `duration`
- `summary`
- `metadata`

event type は少なくとも `hook`、`command`、`codex`、`stage_gate`、`review`、
`recovery`、`browser_observation`、`developer_instruction`、`analysis`、
`proposal`、`application` を表現できるようにする。`metadata` は小さな
structural payload に限定し、secret や巨大 blob を入れない。

logical step 1 では保存形式を line-delimited JSON に固定し、run log directory 配下の
`events.jsonl` を append-only stream として扱う。各行は単独で parse 可能な
event object とし、`run_id` と `event_id` により replay 順序と run 境界を再構成
できるようにする。

### State and store separation

`.sympohy/runs/issue-<number>/state.json` は resume で読む現在地と
heartbeat/lock/recovery 情報を維持する。イベントは state の代替ではなく、
state 更新の根拠として蓄積される。

SQLite observation store は event stream replay の結果として再構築する。
集計クエリ、検索、failure taxonomy 集計、改善提案の入力は store から読むが、
store は必要に応じて再生成できる派生物とする。

`recovery.log` は logical step 1 以降に `recovery` event へ統合する対象であり、
resume 互換性が確認できるまでは移行用の補助 artifact として扱う。

### Logical step 1 scope

logical step 1 の実装範囲は、現行の runner / core / stage-gate / review /
final-verifier / resume 経路の観測境界を明文化し、`state.json` と event stream の
責務分離を固定するところまでとする。

- resume の source of truth は引き続き `state.json` と既存 point artifact に置く。
- event stream は監査・分析用の一次記録として追加し、既存の stale recovery、
  review、final verifier の制御分岐はこの段階では変更しない。
- SQLite observation store、taxonomy、analyzer、proposer、applicator は
  step 2 以降で event stream replay の上に段階追加する。

### Observation capture points

hook 実行時はコマンド名、exit status、duration、短い failure summary を残す。
Codex 実行時は role、model、reasoning effort、prompt hash、parse status、
duration、returncode または failure summary を残す。
stage gate は成功/失敗、gate 名、blocked reason を残す。
review は reviewer role、blocking findings summary、round、status を残す。
recovery は stale 判定理由、resume source、recovery action を残す。
browser observation は console error count、page error count、storage key count、
state hash、accessibility summary を残す。
developer instructions は source kind、path/ref、sha256、summary を残す。

### Failure taxonomy

failure taxonomy は `hook`, `codex`, `command`, `review`, `merge`, `browser`,
`recovery`, `policy`, `data`, `unknown` を最低限の軸として扱う。各 event chain は
failure kind と failure signature を付けられるため、最終的な blocked reason だけ
でなく、どの境界で失敗が連鎖したかを追跡できる。

### Analyzer

analyzer は replay 済み store を入力にし、以下を出力する。

- failure kind 別件数
- phase 滞留時間
- retry 後に解決した failure
- blocked した failure
- recurring event chain pattern

集計結果は人間向け summary と machine-readable JSON の両方に保持し、proposer の
入力として再利用する。

### Proposer

proposer は analyzer の集計と軽量 event chain summary を組み合わせ、改善候補を
JSON で出力する。候補の対象は `prompt`、`hook`、`stage gate`、`docs`、`skill`、
`test`、`config` に限定する。候補には impact、confidence、risk、required
validation を含める。

### Applicator

applicator は low risk な変更のみを受け入れる。具体的には docs、prompt、
test fixture、軽量 config の調整に限り、ソースコードの広範囲修正や自動的な
危険変更はしない。適用後は検証済み draft PR まで進め、それ以上の自動マージは
行わない。

### Regression compatibility

taxonomy、analyzer、proposer schema は replay fixture または equivalent regression
test で互換性を固定する。fixture は event stream の代表例、blocked chain、
retry 後解決、browser observation、developer instruction redaction を含める。

## Test Viewpoints（テスト観点）

- `tests/sympohy/sympohy_runner_test.py`
  - event stream が hook、Codex、stage gate、review、recovery、browser observation
    境界で記録されること。
  - `state.json` の resume 情報が event stream 追加後も維持されること。
  - developer instruction の保存が raw copy ではなく source kind、path/ref、
    sha256、summary になっていること。
  - browser observation が lightweight values のみを保存し、raw screenshot や
    trace を常時保存しないこと。
- `tests/sympohy/sympohy_observability_test.py` もしくは同等の新規テスト
  - event schema、failure taxonomy、analyzer 集計、proposer JSON schema の互換性を
    replay fixture で検証すること。
  - retry 後に解決した failure と blocked failure を分類できること。
  - recurring event chain pattern の集計ができること。
- `tests/sympohy/sympohyWorkflowContracts.test.ts`
  - event summary と self-improvement proposal の string-level contract を保持すること。

## ADR Application（ADR 適用）

`docs/adr/0019-sympohy-llm-loop-observability-self-improvement.md` をこの機能の
durable decision として適用する。event stream を一次記録、SQLite を派生 store、
low risk applicator までの停止点、raw artifact を保存しない方針は ADR で固定し、
design ではその適用方法だけを記録する。

## Open Questions（未決事項）

- analyzer の集計出力に stage ごとの time bucket をどこまで含めるか。
- proposer の候補 JSON に手動承認前提の review context をどの程度載せるか。
- replay fixture を既存の sympohy test suite に追加するか、別 fixture package に
  分離するか。
