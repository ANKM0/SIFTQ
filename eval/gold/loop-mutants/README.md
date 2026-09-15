# 欠陥注入 mutant（T2 検証力 A/B）

検証 phase が実際に欠陥を捕まえるかを測る。LLM を介さず、コマンド層（検証 phase）だけを比較する。

## 手順

1. 基準 commit を固定する。
2. 既知の欠陥を注入する（mutant）。
3. arm A（現行検証）と arm B（e2e を含む検証）を各 mutant に実行する。
4. mutant を revert し、捕獲可否を記録する。

arm の定義は `.taqt/scripts/loop_eval/defect_injection.py` の `ARM_A` / `ARM_B`。arm B は arm A に `task ci:test:e2e` を加えたもの。

## mutant 定義

`eval/gold/loop-mutants/<name>.yaml`:

```yaml
name: boundary-condition-inverted
patch_file: boundary-condition-inverted.patch
expected_catch: true
```

- `patch_file`: 同ディレクトリからの相対パス。`git apply` で適用できる unified diff。
- `expected_catch`: 検証が捕まえるべき欠陥なら true。回帰 mutant（過去のバグ修正の逆適用）は true。

## 実行

```bash
uv run python -m loop_eval.defect_injection --repo . --mutant-root eval/gold/loop-mutants
```

JSON で mutant ごとの捕獲可否と、arm ごとの捕獲率・McNemar 集計（`both_caught` / `a_caught_b_missed` / `a_missed_b_caught`）を出力する。

## 判定

arm B の捕獲率が arm A を上回り、`a_missed_b_caught` が `a_caught_b_missed` を上回ること。誤検知（clean 基準で arm が fail する）が無いことを併せて確認する。
