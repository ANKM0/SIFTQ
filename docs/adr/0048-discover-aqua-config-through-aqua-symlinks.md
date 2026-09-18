# ADR 0048: Discover aqua config in `.config/` through `.aqua/` symlinks

## 決定

- aqua の設定自動探索に乗るため、リポジトリ直下に `.aqua/` を置き、`aqua.yaml` と `aqua-code-mode-host-registry.yaml` を `.config/` の実体への symlink にする。
- `.config/` をツール設定の唯一の源として維持し、ファイルは移動しない。`.aqua/` は探索用の入口に限定する。
- `.aqua/` に `aqua-policy.yaml` は置かない。policy は `.config/aqua-policy.yaml` のまま `AQUA_POLICY_CONFIG`（`.config/env.sh` と Taskfile）で注入する。
- symlink は commit し、欠損・破損時は `task setup:aqua-links`（`scripts/setup_aqua_symlinks.py`）で冪等に復旧する。

### 決定の理由

- aqua は代理実行のため、`AQUA_CONFIG` か「カレントから上位の `aqua.yaml` / `.aqua/aqua.yaml` / `aqua/aqua.yaml`」だけを探索する。`.config/aqua.yaml` は対象外で、#444 以降 bare の `opencode` などが `command is not found` で失敗していた。
- `.aqua/aqua.yaml` を探索させるだけで、`AQUA_CONFIG` を供給する shell や direnv を要さず、proxy 起動の循環を断てる。
- ローカル registry は config からの相対パスで解決されるため、同じ `.aqua/` に symlink を置けば足りる。
- `aqua-policy.yaml` を `.aqua/` に置くと aqua が policy も自動発見し、`aqua policy allow <絶対パス>` を clone/worktree ごとに要求する。policy を探索外に置けばこの運用負荷を避けられる。

## 不採用

- `.config/aqua.yaml` をルート `aqua.yaml` に戻す。
  - ルート直下のファイルを減らす #444 の意図に反するため。
- `.config/` の実体を `aqua/` へ移動する。
  - `.config/` 集約を崩し、`env.sh` / Taskfile / CI / README のパス更新を広げるため。`.aqua/` symlink なら参照を変えずに探索だけ直せる。
- `direnv` と `.envrc` で `AQUA_CONFIG` を供給する。
  - `direnv` 自身も aqua proxy のため `AQUA_CONFIG` が無いと起動できず、設定を届ける前に循環で失敗する。新しいツールと shell hook も増えるため。
- `.config/env.sh` の手動 source のみを維持する。
  - bare の `opencode` は source するまで失敗し続け、再発しやすいため。
- `mise` へ統合する。
  - ツール管理ごと置き換える大規模移行であり、目的に対して過剰なため。

## 補足情報

### 背景

- #444 でルート直下のツール設定を `.config/` へ集約した結果、aqua の探索から外れて bare の `opencode` / `rg` / `node` / `task` が失敗するようになった。

### 制約事項

- `.aqua/` に policy を置かないため、bare の `codex` は policy 無しで失敗する。codex は Taskfile / `.config/env.sh` 経由で `AQUA_POLICY_CONFIG` を設定して実行する。
- symlink の作成には対応するファイルシステムが必要で、WSL / Linux を前提とする。
- `.aqua/` は deny-by-default の `.gitignore` allowlist に登録する。

## 参考リンク

- [aqua の設定ファイル探索](https://aquaproj.github.io/docs/reference/config/)
- [README の Configuration layout](../README.md)
- [Issue #462](https://github.com/ANKM0/SIFTQ/issues/462)
