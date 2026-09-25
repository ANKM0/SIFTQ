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

## 段階3 パイロット（2026-09-24）

- 目的: gold UI 3 件を R=1、`LOOP_VERIFICATION_SKIP_E2E=1` で疎通と粗い差を確認。
- 構成: arm A=`eval/baselines/loop/main_loop_eval.yaml`（opencode-go モデルの現行構造）/ arm B=`eval/baselines/loop/main_loop_minimal.yaml`（checker / post_review を外した構造）。両 arm 同一モデル。
- 結果: `t3-pilot.json`
  - `ISSUE-264-01`: A=human、B=human
  - `ISSUE-293`: A=human、B=human
  - `ISSUE-369`: 20 分でタイムアウト（iteration 7 / fix step で進行中、ハングではない）
- 集計（完了 2 件）: A=closure 0.0 / human 1.0 / cost $0.0436、B=closure 0.0 / human 1.0 / cost $0.0533。
- 読み: 両 arm とも closure 0（human 100%）で **差 0pt（±10pt 以内）**。判定ゲートでは「不明瞭 → A（12 件、R=3）へ拡大」に該当。ただし UI 3 件・R=1 の粗い信号で、両 arm とも閉じられない傾向。
- 補足: `opencode-go/muse-spark-1.3-contributor` で実行（`opencode/muse-spark-1.3-contributor-free` の `stream error` ハングを回避）。usage（tokens / cost）は harness が記録できた。
- 残: A（12 件、R=3、e2e 込み、並列 2〜4）の実行。72 run 規模のため未実施。

## 段階3 比較（A, 2026-09-25）

- 構成: gold 12 件 × R=3 × arm A（現行構造）/ B（最小構造、checker / post_review を外す）、e2e 込み、ローカル並列 4。
- 結果: `t3-comparison.json`
- 集計:
  - A: total 36、done 0、human 36、escaped 0 → closure 0.0% / human 100.0% / escaped 0 / cost $0.9041 / tokens 107.9M
  - B: total 36、done 1、human 35、escaped 0 → closure 2.8% / human 97.2% / escaped 0 / cost $0.7625 / tokens 86.7M
- 判定（`eval/loop-evaluation.md`）:
  1. 必須条件: escaped 0 → 両 arm 満たす。
  2. 主判定: closure 差 +2.8pt、human 差 2.8pt（±10pt 以内）→ タイブレーク。
  3. 最低ライン: 両 arm とも done ≥60% / human ≤30% を大きく未達 → **改修**。
- 結論: **改修**。レビュー構造（checker / post_review）の有無で closure はほぼ変わらない（差 ±10pt 以内）。両 arm とも閉じられない（closure 0〜2.8%、human 97〜100%）ため、verification / routing を先に改修する。段階4（commodity 委譲）は実行しない（簡素化の結論ではないため）。

## 改修: llm 失敗 routing（#534, 2026-09-25）

- 変更: llm step（implement / fix）の失敗を `max_fix_attempts` まで**再試行**する（runner で feedback 別に cap、`main_loop` と eval クローンの `on_failure` を `fix` に）。
- 目的: provider / tool の一時失敗（`feedback=unknown`、空出力で非0）が 1 iteration で human 直行するのを防ぐ（段階1 の human 原因 routing の主因）。
- before（#528 pilot）: 一時失敗で iteration 1 の human 直行が発生。
- after（再実行: pilot 3 件、R=1、`LOOP_VERIFICATION_SKIP_E2E=1`）: 全 run が verification cap（iteration 8）まで再試行。**closure は 0 のまま**（タスク / モデル能力律速）。
- 結果: `t3-pilot-routing-fix.json`

## loop 改良と smoke（#552, 2026-09-26）

- 実装: worktree 衝突の根絶（prune + パス削除 + 再試行）、smoke タスク（`eval/smoke/`）、gold preflight、provider/tool エラーの同一 step 再試行、fix への `last_verification`、verification の全失敗集約、runner の終端優先、write-scope guard（allowed paths）、escalation 分類（`provider_error` / `scope_violation`）。
- smoke（改良前後）: A/B とも done（closure 1.0）。回帰なし。`smoke.json`
- モデル比較: 同一タスク `ISSUE-369` で strong（`opencode-go/deepseek-v4.1-flash`）= done / weak（`opencode-go/muse-spark-1.3-contributor`）= human。**モデル能力が closure に効く**（n=1）。`model-compare.json`
- 7（checker / post_review の要否）: **決定は保留**。部分結果（A3 で B > A）と smoke（A=B）では結論に不足。13 件 A/B の完走後に判断。

## T3: paired replay（#528 で有効化）

ハーネスを #528 で改修した。`loop_eval.replay` は spec の `base_commit` と `repetitions` に対応し、arm × repetition ごとに `git worktree` で隔離 workspace を使う。集計は closure / escaped / human 率 / tokens / n。

残作業:

1. gold タスクを `eval/gold/loop-tasks/` に 30+ 件コミットする（base commit = 正解 PR の first parent）。
2. パイロット（3〜5 件、fast のみ）→ 全量（e2e 込み、並列 2〜4）で実行し、arm (a) 現行 / (b) 最小 loop を比較する。
3. 結果を `eval/results/loop/` に記録し、維持 / 簡素化 / 改修を判定する。

旧メモ（#427 時点）:

- gold が 1 件のみ、対象タスクは既に main に取り込まれており base commit を切っていない（汚染）。
- フル実施は数時間規模の LLM 費用。
