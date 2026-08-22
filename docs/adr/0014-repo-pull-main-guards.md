# ADR 0014: `repo:pull-main` の pull と graphify 更新

## 決定

- `task repo:pull-main` を Taskfile に追加し、repository script `scripts/repo_pull_main.py` を正本として実行する。
- pull の前に `git branch --show-current` が `main` であることと、`git status --porcelain` が空であることを検証する。
- main 以外または dirty worktree の場合は `git pull` を実行せず、理由を標準エラーへ出力して非 0 で終了する。
- ガード判定は副作用のない pure 関数 `guard_error(branch, status_output)` に分離し、単体テスト可能にする。
- ガード通過後は `git rev-parse HEAD` で pull 前の HEAD を記録し、`git pull --ff-only` を実行する。
- pull が失敗した場合は graphify 更新を実行せず、pull の終了コードで止める。
- pull が成功しても HEAD が変わらない場合は graphify 更新を実行しない。
- pull が成功して HEAD が変わった場合だけ `task graphify:update` を実行する。
- pull 後の graphify 更新が失敗した場合は pull を巻き戻さず、graphify の終了コードを非 0 で返す。
- graphify 更新の要否判定は pure 関数 `should_update_graphify(pull_code, head_before, head_after)` に分離する。

### 決定の理由

- main 以外や dirty worktree で pull すると、意図しない merge や未コミット変更の巻き込みが起きるため。
- 判定ロジックを repository script に置くことで、Taskfile を薄い wrapper に保ち（ADR 0001）、自動テストで主要分岐を検証できるため。
- main の更新後にだけ graphify を再生成すれば十分で、HEAD が動かない pull で graphify を更新するコストを避けるため。
- graphify 更新は pull 済みの main を壊さない読み取り系の後続処理であり、失敗時に pull を巻き戻すと利用者の期待と整合しないため。

## 不採用

- Taskfile の `cmds` に判定 shell を直書きする。
  - 分岐のテストが難しく、知識が YAML 内に埋もれるため。
- 人間向けの `git status` 出力で dirty を判定する。
  - 機械可読な `git status --porcelain` より曖昧なため。
- `git diff --quiet` だけで dirty を判定する。
  - untracked file を検出できないため。
- pull の成否にかかわらず graphify を更新する。
  - 失敗した pull の後に更新すると、取得できていない commit で graph を生成するため。
- graphify 更新の失敗時に `git reset --hard` で pull を巻き戻す。
  - pull 済みの main を失わせる破壊的操作であり、更新失敗の通知で十分なため。

## 補足情報

### 背景

- `repo:pull-main` は main を更新する入口であり、pull 前に実行前条件を検証して安全な呼び出しだけを通す。
- Issue #174 の slice 02 で main 以外または dirty worktree で pull しない失敗分岐を、slice 03 で pull 成功と HEAD 更新を条件にした graphify 更新を確定する。

### 制約事項

- `graphify:update` の実行は既存 Task（ADR 0013）を再利用し、runtime 不在時の導入案内を引き継ぐ。
- graphify 更新の失敗では pull を巻き戻さない。利用者は main が更新済みであることをエラーで知り、graphify を修正して再実行する。
- `.codex/rules/siftq.rules` に `task repo:pull-main` の許可 rule を追加し、`ci:lint:codex-task-perms` を満たす。
- エラーメッセージは、利用者が main への switch または変更の commit / stash という次の行動を選べる文言にする。

## 参考リンク

- [Issue #174](https://github.com/ANKM0/SIFTQ/issues/174)
- [ADR 0001](0001-skill-orchestrated-repository-scripts.md)
- [ADR 0013](0013-worktree-scoped-graphify-update-task.md)
