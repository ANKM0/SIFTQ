# E2E 効果測定と再発防止

## baseline（#Phase 0, 2026-09-30）

- 取得: `task -t .config/Taskfile.yml ci:test:e2e:measure`
- 結果: `baseline.json`
- 環境: ローカル `chrome-headless-shell`、`workers: 1`、`retries: 0`
- 集計: **総 76.3s / 88 tests（passed 88, failed 0, flaky 0）**
- 内訳: `matrix.spec.ts` が 51 tests / 51.6s で **全体の 67.7%** を占有。
- 読み: 単一ファイルの直列区間が wall time を支配している。ここを分割・分離しない限り sharding しても 1 shard に偏る。

## 検証観点（一回性）

各 Phase の改修が「今効いたか」を確認する。

- full E2E が緑（`ci:test:e2e`）。
- flake 0（`--repeat-each=3`）。
- sharding 導入時は全 shard 合計が 88 件・重複/欠落なし。
- baseline 比の削減率を `ci:test:e2e:measure` で測定。

## 再発防止ガード（恒久）

- **4-a 規約チェック** `scripts/ci/check_e2e_conventions.py`（`ci:e2e:checks` / `ci:fast:checks`）。
  - `networkidle` の再導入、UI パスワードログイン、`mode: "serial"`、spec の肥大化、config の `trace`/`retries`・`fullyParallel`/`workers` 矛盾を検知。
  - 既存の違反は `scripts/ci/e2e_conventions_allowlist.json` で猶予。**修正したら allowlist から削除する**（削除しても検知は変わらないため、残骸は定期的に掃除する）。
- **4-b 時間バジェット ratchet** `scripts/ci/check_e2e_budget.py`＋`eval/e2e-budget.json`（Phase 4、nightly）。
- **4-c flaky 観測** nightly で `--repeat-each=3`（Phase 4）。

## 使い方

```sh
task -t .config/Taskfile.yml ci:test:e2e:measure   # 計測してサマリ表示
task -t .config/Taskfile.yml ci:e2e:checks         # 規約チェック + ツールのテスト
```
