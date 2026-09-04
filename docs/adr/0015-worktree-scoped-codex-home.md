# ADR 0015: 共有 Codex home とモデル profile

## 決定

- `CODEX_HOME` は通常の taqt 実行で設定しない。Codex の既定 `/home/develop/.codex` を共有する。
- モデルと provider は静的な Codex CLI profile で分離する。
  - `deepseek`: DeepSeek 公式 API の `deepseek-v4-pro`。
  - `muse-spark-opencode-free`: OpenCode Zen の `muse-spark-1.3-contributor-free`。
- profile ごとの catalog JSON は `/home/develop/.codex/models/` に置き、実行中は生成・書換えない。
- taqt は `codex exec --cd <worktree> --profile <profile>` を使う。
  - `main_loop` と `sub_loop` は design / test / checker に `deepseek`、implement / fix に `muse-spark-opencode-free` を使う。
- `--codex-home` は診断用の明示 override として残す。

## 理由

worktree ごとの `.taqt/codex-home/` は model 設定だけでなく skills、認証、plugins、session 履歴も
分散させる。共有 home と静的 profile に分けることで、それらを一箇所に保ちつつモデルの変更範囲を
profile 単位へ限定できる。

編集対象の分離は Codex home ではなく `--cd <worktree>` と Git worktree が担う。

## 運用

- `task codex:profiles:init` は不足する DeepSeek、Muse Free の profile / catalog を作成し、既存ファイルを上書きしない。
  `config.toml` は利用者の OpenAI 設定であり、作成・更新・検証の対象外とする。
- `task codex:profiles:check` は profile、catalog、必要な API key 環境変数を検証する。
- `task codex:codex` は既定 OpenAI 設定、`task codex:deepseek` は DeepSeek V4 Pro、
  `task codex:muse-spark:free` は Muse Free を使う。
- API key は `DEEPSEEK_API_KEY`、`OPENCODE_API_KEY` の環境変数から渡す。TOML、Git、taqt run
  artifact へ保存しない。
- 外部 provider profile は共有している ChatGPT login を変更しない。`forced_login_method` は設定しない。

## 不採用

- worktree ごとの `.taqt/codex-home/`
  - skills・sessionまで不要に分離し、設定生成が実行時の競合要因になるため。
- 共通のモデル catalog
  - 一つのモデルの capability 変更が別 profile に波及するため。
- Docker によるモデル分離
  - profile 選択を解決せず、skills・sessionを共有するには結局 home の mount が必要なため。

## 移行

旧 `switch_codex_profile.py`、qwen profile、`.taqt/scripts/taqt/deepseek.py`、
`.taqt/scripts/taqt/qwen.py`、`taqt:switch:*` は削除する。既存の `.taqt/codex-home/` は Git 管理外の
旧成果物であり、動作確認後に利用者が削除する。

## 参考

- [Issue #273](https://github.com/ANKM0/SIFTQ/issues/273)
- [ADR 0011](0011-resolve-loop-reasoning-effort-in-codex-adapter.md)
