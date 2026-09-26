# loop 妥当性評価の基準

taqt の loop 設計が妥当かを、比較実験で判定するための基準。`eval/results/loop/` に結果を記録する。

## 仮説

- H1: checker / verification / routing が human 率を下げている（レビュー構造に効果がある）。真なら維持。
- H2: human 率の高さは構造の複雑さ由来で、より単純な loop が同等以上。真なら簡素化。
- H3（スコープ外）: fix ループ自体の効果。

## 指標

- closure 率 = done / 終端
- human 率 = human / 終端（run 単位）
- escaped 率 = done かつ held-out 検査失敗 / 試行（見逃し欠陥）
- tokens（input / output / cache）/ 換算コスト
- n（試行数）

有意差は主張しない。小標本（R≥3）のため点推定と n を併記し、マージンで判定する。

## 成功基準（2 段）

| KPI | 目標 | 最低ライン |
|---|---|---|
| closure 率 | ≥ 80% | ≥ 60% |
| human 率 | ≤ 10% | ≤ 30% |
| escaped 率 | 0（非妥協） | 0 |
| コスト / done | ≤ $1 | ≤ $2 |

## 判定フロー

1. 必須条件（安全）: escaped 率 0。どちらかの arm で escaped > 0 なら、その arm は不採用。両方 0 でなければ結論を出さない。
2. 主判定（margin M = ±10pt、closure と human 率で比較）:
   - (b) の closure ≥ (a) − M かつ human 率 ≤ (a) + M → 簡素化（H2 支持）。
   - (a) の closure > (b) + M または human 率 < (b) − M → 維持（H1 支持）。
   - 差が ±M 内 → タイブレーク。
3. 最低ライン判定: どちらも最低ライン未達 → 改修（verification / routing を先に直す）。結論を保留。
4. タイブレーク（差が ±M 内）: 保守コストの低い方を選ぶ → 簡素化を既定。

指標の優先順位: escaped 0 > closure > human 率 > コスト。コストは非悪化の確認に留め、主判定に使わない。

## 実行

- 実行基盤: ローカル。
- 並列度: 2〜4。
- 段階: パイロット 3〜5 件（fast のみ）→ 全量（e2e 込み）。
- arm (a): 現行 taqt。arm (b): 最小 loop = checker / post_review を外した現行（fix は残す）。

## 簡略化の反映（#561）

- #554 で main_loop から checker / post_review を廃止し、implement → verification → fix の簡略構造へ移行した。以降の arm (a) は簡略構造であり、本節より上の checker / post_review 前提の記述は履歴として残す。
- #556 で verification の e2e をフロント変更時のみ実行する。非フロント変更は fast checks までで判定する。
- #534 で provider / tool の一時失敗を同一 step で `provider_retries` まで再試行する。
- 簡略構造の baseline は `eval/baselines/loop/main_loop_eval.yaml` / `main_loop_eval_strong.yaml` / `main_loop_minimal.yaml`。`main_loop_full_structure.yaml` は廃止した。
- 上記の決定は ADR 0068 に記録する。


## 常設化

loop パス（`.taqt/loops/` または `.taqt/scripts/loop/`）を変更する PR では、`eval/results/loop/` の更新または PR 本文に測定結果（harness / command / observed / 採用基準）を記載する。CI は欠落時に warning を出す（block しない）。
