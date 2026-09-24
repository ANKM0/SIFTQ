# loop 効果測定の結果

## T2: 欠陥注入（検証力 A/B）

- 実施日: 2026-09-16
- 基準 commit: `5add261`（#427 マージ後）
- ハーネス: `loop_eval.defect_injection`
- 結果: `t2-defect-injection.json`
- mutant 数: 3
- 集計: arm A（fast のみ）2/3 = 0.667、arm B（+e2e）3/3 = 1.0。`a_missed_b_caught=1`、`a_caught_b_missed=0`、clean 誤検知なし。
- 採用基準: 満たす（arm B 捕獲率 > arm A、差分が e2e 側に有利、clean 誤検知なし）。

## routing リグレッションの決定論的証拠

- 結果: `routing-regression-evidence.json`
- verification 失敗があった run は 9。最終 status は human 8 / done 1。
- `verification_fix` で human へ落ちた run は 9/9。決定論的 verification 失敗が全件 human に流れ、自動 fix の機会が無かった。
- これは LLM リプレイ不要で routing 修正の効果を直接示す。closure の回復量は LLM 依存のため未測定。

## 段階1: human 率（#528, 2026-09-24）

- ハーネス: `loop_eval.human_rate`
- 結果: `human-rate.json`
- 集計（run 単位、全期間累積）: total 201、done 100（closure 49.75%）、human 92（human 率 45.77%）、failed 9。
- human 原因（中粒度 6）: routing 73、verification 8、review 6、spec_product 2、permission 2、model_infra 1。
- 月次: 2026-08 total 87 / human 42、2026-09 total 114 / human 50。
- 注: `unknown` feedback は routing に一括（下位分解は未実施）。blocked_reason はほぼ None のため feedback と permission マーカーで分類。

## T2: 欠陥注入（#525, 2026-09-24）

- 実施日: 2026-09-24
- 目的: #525 の `decide` 畳み込み（loop 定義変更）の回帰確認
- ハーネス: `loop_eval.defect_injection`
- 結果: `t2-defect-injection-525.json`
- mutant 数: 1（`broken-is-task-status`）。`matrix-menu-order-swapped` と `type-error-in-task-title-limit` は patch が現行 tree に適用不可（fixture 陳腐化、main でも同じ）。
- 集計: arm A 1/1、arm B 1/1。`a_missed_b_caught=0`、`a_caught_b_missed=0`、clean 誤検知なし。
- 採用基準: 満たす（arm B が arm A 以上）。
- 注: 本変更は verification の判定を変えないため検証力は不変。

## 段階3 パイロット（2026-09-24, ブロック）

- 目的: gold UI 3 件（ISSUE-264-01 / 293 / 369）を R=1、`LOOP_VERIFICATION_SKIP_E2E=1` で疎通確認。
- 結果: **ブロック**。arm A の implement step で opencode が `opencode/muse-spark-1.3-contributor-free` を呼び、`stream error` の後ハング（15 分超で応答なし、イベントは `step_started` のみ）。
- 原因: opencode provider のモデル利用不可（rate limit / insufficient funds）。ERR-20260924-002 と同型。
- 対応: 実行前に loop のモデルを利用可能な provider（例: opencode-go/*）へ切り替える必要がある。本 PR は harness / spec の準備まで。
- 準備済み: `LOOP_VERIFICATION_SKIP_E2E`、replay の `--repetitions`、12 件の checks 更新。

## T3: paired replay（#528 で有効化）

ハーネスを #528 で改修した。`loop_eval.replay` は spec の `base_commit` と `repetitions` に対応し、arm × repetition ごとに `git worktree` で隔離 workspace を使う。集計は closure / escaped / human 率 / tokens / n。

残作業:

1. gold タスクを `eval/gold/loop-tasks/` に 30+ 件コミットする（base commit = 正解 PR の first parent）。
2. パイロット（3〜5 件、fast のみ）→ 全量（e2e 込み、並列 2〜4）で実行し、arm (a) 現行 / (b) 最小 loop を比較する。
3. 結果を `eval/results/loop/` に記録し、維持 / 簡素化 / 改修を判定する。

旧メモ（#427 時点）:

- gold が 1 件のみ、対象タスクは既に main に取り込まれており base commit を切っていない（汚染）。
- フル実施は数時間規模の LLM 費用。
