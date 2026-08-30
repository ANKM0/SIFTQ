# ADR 0015: worktree ごとの Codex 設定保存先と起動 Task

## 決定

- `CODEX_HOME` は profile ごとの相対パス `.taqt/codex-home/<profile>` を worktree root 基準で解決する。
  - main worktree では `<repository>/.taqt/codex-home/<profile>`。
  - 各 taqt worktree では `<repository>/.taqt/worktrees/<task>/.taqt/codex-home/<profile>`。
- `taqt:run`、`taqt:auto`、`taqt:worker` が Codex を起動する loop 実行時は、解決済みの `CODEX_HOME` を main / deepseek / qwen の各 profile で子プロセスへ渡す。
- `taqt:switch:main` / `taqt:switch:deepseek` / `taqt:switch:qwen` は同じ解決済み `CODEX_HOME` へ profile 設定を書き込み、`codex login` / `codex logout` も同じ `CODEX_HOME` で実行する。
- `--codex-home` による CLI override を最優先し、次に profile の `codex_home`、最後に profile ごとの既定値を使う。
- `.taqt/codex-home/` は worktree ごとのローカル成果物として Git の追跡対象外とする。

### 決定の理由

- worktree ごとに Codex の config / model / auth を分離し、`/model` や profile 切替の変更が他 worktree へ波及するのを防ぐため。
- 相対パスを worktree root 基準で解決することで、main と各 taqt worktree で安定した別々の保存先を再現できるため。
- Taskfile に path を直書きせず、repository script と profile 設定を正本にして知識の重複を避けるため（ADR 0001）。

## 不採用

- 全 worktree で `~/.codex-deepseek` を共有する。
  - worktree 間で設定変更が波及し、分離の目的を満たさないため。
- カレントディレクトリ基準で `CODEX_HOME` を解決する。
  - 呼び出し位置によって保存先が変わり、安定した割り当てにならないため。
- ハッシュ値だけの保存先を使う。
  - worktree との対応が読み取りにくく、利用者が設定を確認・削除しにくいため。

## 補足情報

### 背景

- Codex の既定設定は `~/.codex` を共有するため、worktree ごとの設定変更を分離できない。
- taqt の loop 実行は `task_run` が子プロセスへ `CODEX_HOME` を渡す唯一の入口であり、profile 切替も同じ保存先へ揃える必要がある。

### 制約事項

- main profile の設定は利用者が `~/.codex/config.main.toml` に保持する main 用テンプレート、または `~/.codex/backup-deepseek/config.toml` から worktree の `CODEX_HOME` へ複製する。
- main profile の認証は worktree ごとの `CODEX_HOME` に対して `codex login` を実行して確立する。
- deepseek profile は design に DeepSeek の `deepseek-v4-pro`、実装系 agent に OpenRouter の `qwen/qwen3.8-flash` を使う。API key は `DEEPSEEK_API_KEY` と `OPENROUTER_API_KEY` から受け取り、認証情報を config へ書き込まない（ADR 0011 の reasoning effort 解決は変更しない）。
- qwen profile は API key を `OPENROUTER_API_KEY` から受け取り、OpenRouter の `qwen/qwen3.8-flash` を使う。認証情報は config へ書き込まない。
- `taqt:switch:qwen` と `codex:qwen` は新規 Taskfile 名のため、`.codex/rules/siftq.rules` へ対応する allow rule を追加する。

## 参考リンク

- [Issue #174](https://github.com/ANKM0/SIFTQ/issues/174)
- [ADR 0001](0001-skill-orchestrated-repository-scripts.md)
- [ADR 0011](0011-resolve-loop-reasoning-effort-in-codex-adapter.md)
