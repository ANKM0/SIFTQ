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

## T3: paired replay（保留）

保留。理由:

- #427 の主眼である routing 修正は上記で決定論的に検証済み。T3 の追加対象は loop 構造（design/test 廃止）の closure 効果のみで、refacta も従属証拠・ノイズ大と位置づける。
- gold が 1 件のみ、対象タスクは既に main に取り込まれており base commit を切っていない（汚染）。
- `loop_eval.replay` は arm 間で workspace をリセットせず、R>=3 集計も外部。フル実施は数時間規模の LLM 費用。

T3 は「loop を継続的に変更する時の回帰ガード」として、次の loop 変更時に有効化する。有効化に必要な作業:

1. gold に base commit / 期待 checks を持たせる（10〜20 件）。
2. arm ごとに `git worktree add <ws> <base_commit>` した隔離 workspace を使う（単一 arm spec で実行すればハーネス改修なしで持ち越しを排除できる）。
3. R>=3 で closure / escaped / human 率 / 自動復帰率 / コストを集計する。
