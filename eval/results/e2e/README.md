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
- **4-b 時間バジェット ratchet** `scripts/ci/check_e2e_budget.py`＋`eval/e2e-budget.json`（`ci:e2e:budget`、nightly）。既定は `warn_only`。安定後に外して fail 化する。
- **4-c flaky 観測** `.github/workflows/e2e-nightly.yml` で `--repeat-each=3`。

## 結果（2026-09-30）

ローカル単一ランナー（wall time）:

| 段階 | 総時間 | tests | 内容 |
| --- | --- | --- | --- |
| baseline | 76.3s | 88 | `workers: 1`、全ログイン、`matrix.spec.ts` 直列 51 |
| Phase 1 | 50.7s | 89 | storageState でログイン 1 回化、`networkidle` 廃止 |
| Phase 2 | 53.9s | 89 | `matrix.spec.ts` を 4 ファイルへ分割、serial 解除 |

- 単一ランナーは 76.3s → 約 51–54s（**約 -30%**）。Phase 2/3 は単一実行の wall を変えない（並列化は CI の効果）。

CI e2e（run `36707506856`、**キャッシュ cold**）:

| | 変更前 | 変更後 |
| --- | --- | --- |
| e2e wall | 1m52s（単一ジョブ） | 約 61s（4 shard 並列、最大 shard 1m1s） |
| shard 別 job | — | 54s / 57s / 61s / 59s |

- shard 別 test 数: 24 / 21 / 22 / 21（chromium 88）＋ setup 各 shard 1 = 89、重複/欠落なし。
- **wall はテスト 1/4 にはならない**。shard 1 の内訳: setup 約 18s（`bun install` 3.9s＋`playwright install`/migration 11.2s）＋ test 19.1s。この run は node_modules と Playwright のキャッシュが両方 miss した cold 実行。
- `ci:test:e2e:setup` は cache-aware（`node_modules/.bun-lock-hash` 一致で `bun install` スキップ、Chromium バイナリ有無で `playwright install` スキップ）。warm では setup が数秒まで落ちる。


## 使い方

```sh
task -t .config/Taskfile.yml ci:test:e2e:measure           # 計測してサマリ表示
task -t .config/Taskfile.yml ci:e2e:checks                 # 規約チェック + ツールのテスト
task -t .config/Taskfile.yml ci:e2e:budget                 # 直近の計測を予算と比較
task -t .config/Taskfile.yml ci:test:e2e -- --shard=1/4    # shard 実行
```
