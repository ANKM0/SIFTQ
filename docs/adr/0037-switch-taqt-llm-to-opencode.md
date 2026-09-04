# ADR 0037: taqtのLLM実行をopencode直呼びに一本化する

## 決定

- taqtのLLM実行を `codex exec` 経由から `opencode run` 直呼びに一本化する。
- loop yamlの `model` はフルID（`provider/model`）で表記し、`reasoning_effort` は `--variant` に写像する。
- headless実行の権限は `opencode.json` のdeny backstopと `opencode run --auto` の併用とする。

### 決定の理由

- `muse-spark-1.3-contributor-free` をcodex経由で呼ぶと `Recursive JSON schemas are not currently supported` で失敗する。障害層はCodexのResponsesラッパーにある。
- 同モデルの `opencode run -m` 直呼びは成功する。`deepseek/deepseek-v4-pro` の直呼びも成功するため、codex経路の残存理由がない。
- opencodeは `.agents/skills/` をネイティブ探索するため、skill基盤の移行コストがない。

## 不採用

- codex経路の部分的残存（deepseek系のみcodex維持）
  - adapter二重維持のコストが残り、障害層の切分けが複雑になる。
- `model` のベアslug＋補完規約
  - `deepseek-v4-pro` だけでも4候補（`opencode/`、`deepseek/`、`opencode-go/`、`openrouter/`）があり誤爆しうる。

## 補足情報

### 背景

- `main_loop` の `implement/fix` が `muse-spark-opencode-free` profileで失敗し、fallbackの `deepseek` に退避していた。
- codexの5h limit回避用に分離されていた `main/sub_loop` と `fallback→deepseek` は、opencode移行後にrate limit用の単一fallbackへ置き換える。

### 制約事項

- codex資産の削除は実走検証の後に行う。本ADRの実装では両対応を残す。
- session改善スキャンのopencode対応化は後続issueに分ける。
- `~/.codex` 配下の整理はマシンローカルのため対象外とする。

## 参考リンク

- `opencode run --help`（`-m provider/model`、`--variant`、`--auto`）
- https://opencode.ai/docs/permissions/
- https://opencode.ai/docs/skills/
