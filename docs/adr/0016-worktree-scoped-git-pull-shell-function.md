# ADR 0016: worktree ごとの `git pull` 振り分け shell function

## 決定

- `scripts/yoriwake_git_pull.sh` を追加し、Yoriwake の interactive shell で source して使う。
- shell function `git` は、引数のない `git pull` かつカレントディレクトリが Yoriwake clone 配下の SIFTQ worktree である場合だけ `task repo:pull-main` を実行する。
- worktree の判定は次の両方を満たすこととする。
  - `git rev-parse --show-toplevel` が script の source 元 clone root と同一、またはその配下。
  - worktree root に `.taqt/config/profiles.yaml` と `taskfile/core.yml` が存在する。
- それ以外の Git コマンドは `command git "$@"` で素の Git へ委譲する。
- `command git pull [args...]` は function を迂回して素の Git を実行する。
- `git pull` 以外の Git コマンドや引数付きの `git pull` は wrapper で振り分けない。

### 決定の理由

- Git alias は組み込みの `pull` を置き換えられないため、shell function を使う。
- source 元 clone root と SIFTQ の repository marker の両方で判定し、任意の Git repository や Yoriwake 配下の別 repository へ影響させないため。
- `command git` は shell 標準の function 迂回手段であり、追加の escape hatch option を設ける必要がないため。
- 引数付きの `git pull` は `repo:pull-main` の固定した `git pull --ff-only` の意味と一致しないため、素の Git に委譲して引数を失わせないため。

## 不採用

- Git alias で `pull` を置き換える。
  - Git は組み込みコマンドを alias で置き換えられないため。
- 任意の Git repository で `git pull` を置き換える global wrapper。
  - Yoriwake 以外の repository の pull を変更するため。
- `-o` を escape hatch に使う。
  - `git -o` は Git 自身の option と衝突するため。
- 引数付きの `git pull` も `task repo:pull-main` へ振り分ける。
  - `repo:pull-main` は引数を取らない固定操作であり、利用者の引数を失わせるため。

## 補足情報

### 背景

- main の更新後だけ graphify を更新する `task repo:pull-main`（ADR 0014）を、Yoriwake の日常的な `git pull` から安全に呼び出せるようにする。
- shell function は Yoriwake の interactive shell に限定し、repository 外や別 repository の Git 操作は変更しない。

### 制約事項

- 導入は Yoriwake の interactive shell 設定へ次の 1 行を追加する。
  - `source /home/develop/Yoriwake/scripts/yoriwake_git_pull.sh`
- 解除は新しい shell を開くか、次のコマンドで function を削除する。
  - `unset -f git _yoriwake_git_worktree`
- 素の `git pull` を使う場合は `command git pull [args...]` を実行する。
- 対象 shell は Bash とする。他の shell へは Yoriwake-base の導入手順と合わせて対応しない。

## 参考リンク

- [Issue #174](https://github.com/ANKM0/SIFTQ/issues/174)
- [ADR 0001](0001-skill-orchestrated-repository-scripts.md)
- [ADR 0014](0014-repo-pull-main-guards.md)
