# loop 効果測定の結果

## T2: 欠陥注入（検証力 A/B）

- 実施日: 2026-09-16
- 基準 commit: `5add261`（#427 マージ後）
- ハーネス: `loop_eval.defect_injection`
- 結果: `t2-defect-injection.json`
- mutant 数: 3
- 集計: arm A（fast のみ）2/3 = 0.667、arm B（+e2e）3/3 = 1.0。`a_missed_b_caught=1`、`a_caught_b_missed=0`、clean 誤検知なし。
- 採用基準: 満たす（arm B 捕獲率 > arm A、差分が e2e 側に有利、clean 誤検知なし）。

## T3: paired replay

未実施。以下の阻害要因がある。

- gold タスクが 1 件のみ（目標 10〜20）。
- `eval/gold/loop-tasks/ISSUE-140-01.yaml` のタスクは `status: done` で既に main に取り込まれており、base commit を切っていないため現行 main での replay は汚染される（解が既に存在）。
- `loop_eval.replay` は arm 間で workspace をリセットしない。arm A の変更が arm B に持ち越される。
- R>=3 の反復は呼び出し側で行う必要があり、集計は外部。

T3 を有効化するには、gold に base commit を持たせて隔離 workspace を arm ごとに用意し、リプレイハーネスに workspace リセットを追加する必要がある。詳細は #434。
