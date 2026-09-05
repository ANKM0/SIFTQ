# CI 10秒化の改善案

現状は約76秒（`33895257776`）。

## 現状内訳

| 区間 | 時間 | 備考 |
|---|---|---|
| `setup-vp` | 約10秒 | 全体の約13% |
| `aqua install` | 約4秒 | codex/d2/opencode等を含む |
| `vp lint .` + `vp lint src tests` | 計約6秒 | 重複。二重実行 |
| `typecheck` + `build`内`tsc` | 計約6秒 | `tsc`重複 |
| `ci:test`内Playwright | 約30秒 | ブラウザDL約12秒＋D1＋e2e。vitest自体は2.3秒 |
| `knip` | 約1.4秒 | |
| Python系check8種 | 計約1秒 | 速い。問題なし |

10秒は直列のままでは不可能。方針は「分割＋キャッシュ＋除外」のみ。

## 改善案

1. 重複lintの統合：効果約3秒、コスト小
   - `ci:lint`（`.`）と`ci:lint:ts-fast`（`src tests`）は包含関係。`vp lint .`一本化で約2.5秒削減。

2. `tsc`重複の解消：効果約2〜3秒、コスト小
   - `typecheck`と`build`（`tsc && wrangler deploy --dry-run`）で`tsc`が2回走行。`build`を`--dry-run`のみ、あるいは`tsc --noEmit`一本化。

3. Playwrightの分離・軽量化：効果約25〜30秒、コスト中
   - 最大のボトルネック。選択肢は3つ。
   - a. `install chromium`を`install --only-shell chromium`にし、`PLAYWRIGHT_BROWSERS_PATH`を`actions/cache`する（約10秒削減）。
   - b. e2e自体をPRゲートから外し、`ci-extended` / nightlyへ移動（約30秒削減）。fast gateを10秒化するなら必須。

4. ジョブ並列化：効果は壁時計で約1/3〜1/5、コスト中
   - 単一`ci`ジョブの直列20タスクを、`fast` / `type-test` / `build` / `e2e`の4並列へ。壁時計は最長ジョブに収束。
   - `paths-filter`併用でdocsのみ変更時はheavy jobをskip。

5. セットアップのキャッシュ化：効果約10秒、コスト中
   - `setup-vp`約10秒、`aqua install`約4秒、`bun install`は現状16msで問題なし。
   - `~/.local/share/vite-plus`、`~/.local/share/aquaproj-aqua`、`PLAYWRIGHT_BROWSERS_PATH`、`UV_CACHE_DIR`、bun storeを`actions/cache`する。
   - さらに`aqua.yaml`をjob毎に分割し、fast jobでは`task`+`rg`のみinstall。全量installをやめる。
   - `fetch-depth: 0`を`1`へ（commitlintは`fetch-depth`不要なbase/head取得に変更）。

6. 自作コンテナ化：効果約12秒、コスト大
   - 上記ツール焼き込み済みイメージで`container:`実行。セットアップ自体を消去。5.で足りなければ検討。

## 10秒達成の構成案

fast gate（required、10秒目標）とextended（非blocking）に分割する以外に道はない。

- `ci-fast`：checkout＋cache hit＋python checks＋`vp lint .`＋`tsc --noEmit --incremental`＋vitestのみ。見積約8〜9秒。
- `ci-extended`：depcruise/knip/jscpd/build/e2e/audit。PRマージ条件にしないか、`merge_group`のみ実行。

## 推奨順序

1. Phase 1（設定のみ）：1＋2＋3a＋5のキャッシュ。目標約30秒。
2. Phase 2：4の並列化＋`paths-filter`。目標約15秒（e2e除く最長job）。
3. Phase 3：3bのゲート分割。fastのみで約10秒。

## e2e分離時のflaky対策

外すのは実行タイミングであり、検出自体は維持する。検出の場を移す。

現状のe2eは`matrix.spec.ts`12件・serial・`retries: 0`。`networkidle`待ちや`Date.now()`依存があり、PRゲートに置くとflakyが全PRを止める。これが分離の理由でもある。

1. `merge_group`と`main` pushでは必須実行にする。PRでは非blocking、merge直前にblocking。マージ前の検出は維持できる。
2. UI変更時のみPRでも任意実行する。`paths-filter`で`src/**`変更時に`ci-extended`を手動/自動トリガし、無関係PRの待ちを消す。
3. nightlyでflake率を計測する。extended側は`retries: 2`＋`--shard`＋レポーター出力とし、リトライ成功＝flakyとして記録する。現状の`retries: 0`はflakeと真の失敗を区別できない。
4. 縮小と移譲をする。API/UI契約は`tests/bdd`のcontract testがfast gateに残るため、大半の回帰はPRで検出できる。e2eはクリティカルパス（signIn→作成→表示）に絞り、件数を減らしてflake母数を下げる。

要約すると、PR高速化と安全性は「PR任意＋merge必須＋nightly計測」の三層で両立する。

## e2e記述ルール：時間依存のsleepを入れない

`Date.now()`をタイトル一意化に使う、`waitForTimeout`で固定sleepする等の時間依存処理はflakyの温床であり、禁止する。

- 一意値は時刻ではなく`testInfo.testId`や連番等の決定的値から生成する。
- 待機は`toBeVisible`・`toHaveURL`等の条件待機のみ使う。`networkidle`等の曖昧な条件も避け、対象要素の可視性で待つ。
- 新規e2e追加時は本ルールへの適合をレビュー観点にする。

## 実測（#336 Phase 1〜3実施後）

対象run：`33900233834`（全job成功、ブラウザcacheはcold）。

| job | 時間 | 備考 |
|---|---|---|
| changes | 6秒 | docsのみ変更時はextended/e2eをskip |
| fast | 31秒 | 内訳：setup約13秒（checkout 3＋cache restore 6＋bun 1＋他）＋gate約14秒（lint 3＋tsc 3＋vitest 2＋install類） |
| extended | 19秒 | build＋duplicate＋dead-code |
| e2e | 46秒 | cold（ブラウザDL約12秒含む）。warm時は約32秒見込み |
| 壁時計 | 約55〜59秒 | baseline 76秒から約25%短縮 |

目標との対比：

- Phase 1「CI全体約30秒」：未達。単一jobのままではe2e約30秒＋setup約20秒が残る。
- Phase 2「e2e除く最長約15秒」：未達。extended 19秒、fast 31秒。job毎のcheckout＋setup約13秒が下限を押し上げる。
- Phase 3「fast約10秒」：未達。hosted runnerではsetup約13秒＋gate約14秒が下限。10秒にはツール焼き込み済みコンテナ（改善案6）が必要。

採用しなかった施策と理由：

- bun store / uv cache：restore（約4秒/約1秒）がinstall（約1秒/約0.1秒）を上回り逆効果のため削除。
- `fetch-depth: 1`：commitlintがbase..headの履歴を必要とするため`0`を維持。
- `aqua.yaml`のjob毎分割：cache hit時の`aqua install`スキップで同等効果のため見送り。

残課題（別issue化を推奨）：自作コンテナ化によるsetup約13秒の消去。

## 追加高速化（#338 follow-up）

Phase 1〜3後の追加計測で、fast jobのsetupが主な残ボトルネックと判明した。

- `setup-vp`は、`bun install`で導入される`node_modules/.bin/vp`をPATHへ追加することで不要になる。
- aquaはCIで必要な`task`・`uv`・`rg`のためだけに使われていたため、`go-task/setup-task`・`astral-sh/setup-uv`へ分離する。`rg`はrunner標準を利用する。
- `node_modules`を`bun.lock`キーで直接キャッシュする。Bun storeの復元はinstallより遅かったため採用しない。
- fastの独立チェックとextendedの静的チェックをTaskの並列`deps`へ移す。
- commit message checkをchanges jobへ移し、fast jobの処理から外す。
- docs-only変更では同じrequired job名のまま`ci:docs-fast`へ切り替え、frontend依存を導入しない。
- feature branchのpushをCI対象から外し、`pull_request`と`main` pushだけを対象にする。同じcommitのpush/PR二重実行を防ぐ。

これにより、通常のPRではfast gateの処理を約10秒未満、docs-only変更では約1秒のローカルtask処理まで短縮できる見込みである。ただしGitHub Actionsのrunner起動・checkout・action実行時間を含むjob全体の10秒達成は、hosted runnerでは別途検証が必要である。

### 追加施策の実測

対象run：`33948721805`（追加施策反映後、全job成功、node_modules cache hit）。

| job | 時間 | 備考 |
|---|---:|---|
| `changes` | 5秒 | commit message checkを移動済み |
| `fast` | 22秒 | setup約11秒、fast gate約7秒 |
| `extended` | 19秒 | setup込み。静的checkは並列実行 |
| `e2e` | 41秒 | Playwright browser cache hit、setup込み |
| 壁時計 | 約54秒 | feature branchのpush runは発生せずPR runのみ |

追加施策の効果：

- `setup-vp`とVite+ cacheを削除し、`node_modules/.bin/vp`を利用した。
- aqua cacheを削除し、`go-task/setup-task`と`astral-sh/setup-uv`へ分離した。
- `node_modules`（約254MB）を直接cacheし、frontend installを約10msまで短縮した。
- fast gateの独立checkを並列化し、ローカルの`task ci:fast`は約0.8〜2.6秒で完了した。
- docs-only変更は`ci:docs-fast`へ分岐し、frontend依存を導入しない。
- feature branchのpush triggerを削除し、同一commitのpush/PR二重実行を解消した。

残る制約：hosted runnerのjob setupが約11秒あるため、fast job全体の10秒は未達。10秒をjob全体のSLOとする場合は、Task・uv・Bun・依存を焼き込んだcontainer、または常駐self-hosted runnerが必要である。
