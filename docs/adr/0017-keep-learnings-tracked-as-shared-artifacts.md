# ADR 0017: `.learnings` を共有追跡成果物として維持する

## 決定

- `.learnings/LEARNINGS.md`、`.learnings/ERRORS.md`、`.learnings/FEATURE_REQUESTS.md` は Git の追跡対象かつ PR でレビュー・マージする共有成果物として維持する。
- `.learnings/` を `.gitignore` に追加しない。Issue #174 で追加する ignore は `graphify-out/` と `.taqt/codex-home/` の worktree ローカル成果物に限定する。
- `.learnings/*.md` の差分はコードと同様に PR レビュー対象とする。

### 決定の理由

- learnings / errors / feature requests は作業者間で共有すべき知識であり、Git の履歴と PR レビューを経由して追跡するため。
- worktree ごとの Codex 設定と graphify 出力は分離するが、学習成果物までローカル化すると知識が失われるため。
- self-improvement skill の team-wide 方針（`.learnings/` を `.gitignore` に追加しない）と一致させるため。

## 不採用

- `.learnings/` を `.gitignore` に追加して worktree ごとにローカル化する。
  - 共有知識が Git の追跡対象から外れ、PR レビューで共有できないため。
- `.learnings/*.md` を `repo:pull-main` や graphify 更新の後処理で自動 commit する。
  - 未レビューの変更が混入し、PR でレビュー・マージする目的に反するため。
- `graphify-out/` を追跡対象に追加する。
  - 再生成可能な worktree ローカル成果物のため。ADR 0013 の判断を維持する。

## 補足情報

### 背景

- Issue #174 は worktree ごとに Codex 設定と graphify 出力を分離する。その際、共有すべき `.learnings/` とローカル成果物の区別を明確にしておく。
- slice 08 は `.learnings/LEARNINGS.md`、`.learnings/ERRORS.md`、`.learnings/FEATURE_REQUESTS.md` が PR でレビュー・マージ可能な追跡対象のままであることを確定する。

### 制約事項

- この 3 ファイルは `git ls-files` に現れ、`git check-ignore` で ignore されない状態を維持する。
- `.gitignore` には `.learnings/` を追加しない。`graphify-out/` と `.taqt/codex-home/` の ignore は維持する。
- 追跡状態と非 ignore はテストまたは CI で検証する。
- 本 ADR は slice 08 の範囲のみ定め、`graphify-out/` の ignore 維持は ADR 0013 と後続 slice で検証する。

## 参考リンク

- [Issue #174](https://github.com/ANKM0/SIFTQ/issues/174)
- [ADR 0001](0001-skill-orchestrated-repository-scripts.md)
- [ADR 0013](0013-worktree-scoped-graphify-update-task.md)
