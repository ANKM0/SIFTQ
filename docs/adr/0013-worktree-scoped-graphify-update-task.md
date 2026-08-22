# ADR 0013: worktree ごとの graphify 更新 Task

## 決定

- `task graphify:update` を Taskfile に追加し、実行対象 worktree の root（`.ROOT_DIR`）を `graphify update` へ渡す。
- `graphify` が PATH にない場合は自動インストールせず、導入方法を含むエラーを表示して非 0 で終了する。
- `graphify-out/` は worktree ごとのローカル成果物として、引き続き Git の追跡対象外とする。

### 決定の理由

- worktree ごとにグラフを分離し、main 更新後の再生成や別 worktree の成果物混入を防ぐため。
- 導入を暗黙に進めると環境変更の副作用が広がるため、不足時は明示的な導入手順で止める。

## 不採用

- `graphify` 不在時に Task が `uv tool install graphifyy` を自動実行する。
  - Task の副作用で利用者環境を変更し、失敗時の状態も複雑になるため。
- 実行時のカレントディレクトリまたは include 元の `TASKFILE_DIR` を更新対象にする。
  - カレントディレクトリは呼び出し位置に依存し、`TASKFILE_DIR` は include された `taskfile/core.yml` のディレクトリを指すため、worktree root を安定して指せない。
- `graphify-out/` を Git に追加して共有する。
  - 再生成可能なローカル成果物であり、差分とマージの管理対象にしないため。

## 補足情報

### 背景

- Git worktree はコードを分離するが、graphify はカレントディレクトリ配下へ `graphify-out/` を生成する。Task から更新対象を明示しないと、呼び出し位置によって出力先が揺れる。
- Issue #174 の slice 01 として、まず `task graphify:update` の更新対象と runtime 不在時の挙動を確定する。

### 制約事項

- `graphify` コマンドは利用者または環境側で導入済みであることを要求し、Task は導入状態の検査と更新実行のみを担う。
- 導入方法のエラーは `uv tool install graphifyy` と `python3 -m pip install graphifyy` の両方を提示する。
- `task graphify:update` の追加時は、Codex の Task 許可 rule（`.codex/rules/siftq.rules`）にも `task graphify:update` を追加する。
- この ADR は slice 01 の範囲を定め、`repo:pull-main` や `CODEX_HOME` の分離は後続 slice で扱う。

## 参考リンク

- [Issue #174](https://github.com/ANKM0/SIFTQ/issues/174)
- [ADR 0001](0001-skill-orchestrated-repository-scripts.md)
