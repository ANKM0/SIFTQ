# ADR 0049: Place committed tool config in `.config` and generated artifacts in `tmp`

> Status: Superseded by [ADR 0064](0064-keep-committed-configuration-under-config.md), [ADR 0065](0065-keep-generated-artifacts-under-tmp.md)

## 決定

- commit する設定は `.config/`、生成物・キャッシュ・一時ファイルは `tmp/` に置く。
- `tmp/` を生成物の唯一のルート集約先とし、`.venv` / `.ruff_cache` / `.pytest_cache` / Playwright の出力 / Wrangler の local state を `tmp/` 配下へ向ける。
- ルートに散っていた死んだ生成物と重複生成物は削除する。

### 決定の理由

- 設定（backup・レビュー対象）と生成物（削除可能）はライフサイクルが異なる。XDG Base Directory も config と cache/state を分けることを求める。
- `.config` に生成物を混ぜると、commit 対象と ignore 対象が同居し、allowlist が複雑化する。
- 生成物の出力先は各ツールの設定で `tmp/` に向けられる（`UV_PROJECT_ENVIRONMENT` / `RUFF_CACHE_DIR` / pytest `cache_dir` / Playwright `outputDir` / wrangler `--persist-to`）。既存の `tmp/` 直下（uv-cache 等）とも一致する。

## 不採用

- 生成物を `.config/` に置く。
  - config と cache のライフサイクルが混ざり、backup と削除の境界が曖昧になるため。
- `var/` や `dev/` などの新しい umbrella を追加する。
  - 既存の `tmp/` で足りる。新しい名前は慣例の学習コストを増やすため。
- `graphify-out/` を `tmp/` へ移す。
  - `graphify install` が skill・MCP 設定・git hook に literal `graphify-out/` を埋め込むため、ツール制約としてルート固定の例外とする。

## 補足情報

### 背景

- #444 でツール設定を `.config/` へ集約したが、生成物の置き場は統一されておらず、ルートと `.config` に重複が残っていた。

### 制約事項

- `node_modules/` はパッケージマネージャの制約でルート固定。
- `graphify-out/` は graphify の制約でルート固定。
- `.config/.wrangler/tmp` は wrangler の bundling temp が config ディレクトリ基準のため残る。
- `tmp/` は生成物の永続先なので、`tmp/release-*` の git worktree を消す場合は `git worktree prune` が必要。

## 参考リンク

- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/)
- [README の Configuration layout](../README.md)
- [Issue #465](https://github.com/ANKM0/SIFTQ/issues/465)
