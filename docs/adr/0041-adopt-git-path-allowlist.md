# ADR 0041: Git の untracked ファイルを deny-by-default の path allowlist で管理する

## 決定

- Git の untracked ファイルは、`.gitignore` を deny-by-default の path allowlist として管理する。
- リポジトリのソース、テスト、文書、設定、マイグレーション、共有開発成果物は明示的に許可する。
- 生成物、作業状態、依存関係、環境変数、秘密情報などは明示的に拒否する。
- このルールは意図しないコミットを防ぐ Git 運用上のガードであり、秘密情報を完全に保護するセキュリティ境界とは扱わない。

### 決定の理由

- 未知のローカルファイルを個別に ignore し忘れても、既定では Git の追加対象にならない。
- allowlist により、追跡対象とローカル成果物の境界を `.gitignore` から確認できる。
- このリポジトリには `.learnings/`、`.agents/`、`.codex/` など共有すべき成果物があり、path 単位で許可範囲を表現できる。

## 不採用

- 個別の deny-list を維持する方式
  - 新しいローカル生成物やエージェント用ファイルを ignore し忘れる余地が残るため。
- 拡張子だけで許可する方式
  - 許可された拡張子の秘密情報や生成物まで許可する可能性があり、path 単位の境界を表現できないため。
- `.learnings/`、`.agents/`、`.codex/` をまとめて ignore する方式
  - 共有成果物や開発環境の正本を Git の追跡対象から外すため。

## 補足情報

### 背景

- 現在の `.gitignore` は `node_modules/`、`graphify-out/`、`.taqt/runs/` などを個別に除外している。
- `.taqt/` には共有設定・スクリプトとローカル状態が混在するため、ディレクトリ全体ではなく path 単位の許可・拒否が必要である。
- `.learnings/` は ADR 0017 により共有追跡成果物として維持し、`graphify-out/` は ADR 0013 により worktree ローカル成果物として除外する。
- 実装と検証は Issue #385 で行う。

### 制約事項

- `.gitignore` は既に追跡済みのファイルには適用されないため、既存の秘密情報や履歴の除去はこの ADR の対象外とする。
- `git add -f` などの強制操作は `.gitignore` で禁止できないため、別の権限制御や CI 検査が必要な場合は別途判断する。
- 新しい共有成果物を追加する場合は、`.gitignore` の allowlist と対応する検証を同時に更新する。
- 親ディレクトリを許可しないと Git が配下を評価できないため、allowlist の順序と親ディレクトリの再許可を検証する。

## 参考リンク

- [記事: .gitignore everything by default](https://packagemain.tech/p/gitignore-everything-by-default)
- [ADR 0013: worktree ごとの graphify 更新 Task](0013-worktree-scoped-graphify-update-task.md)
- [ADR 0017: `.learnings` を共有追跡成果物として維持する](0017-keep-learnings-tracked-as-shared-artifacts.md)
- [Issue #385](https://github.com/ANKM0/SIFTQ/issues/385)
