# AGENTS.md

## リポジトリ共通ルール

- このリポジトリは SIFTQ の local-first task matrix application である。
- 既存の設計、文書、Taskfile、`.codex/rules/` を優先する。
- ユーザーの明示指示がある場合を除き、無関係なリファクタリングや履歴整理をしない。
- 既存の未コミット変更はユーザー作業として扱い、明示依頼なしに戻さない。
- 探索は `rg` / `rg --files` を優先し、必要な範囲だけ読む。
- 文章は簡潔かつ必要十分にし、削れる語は削る。

## 作業フロー

- loop engineering の方針は `docs/design/#134.md` を基準にする。
- requirements と wireframes の扱いが未決なら `docs/design/#134.md` を基準に判断する。

## Codex と自動化

- `.codex/rules/siftq.rules` の command permission rules を尊重する。
- taqt 実装は `.taqt/`、補助 script は `scripts/` を基準にする。
- 通常の Codex user config と repository rules を無効化しない。
- `CLAUDE.md` や role 別の `AGENTS.md` を増やす前に、root `AGENTS.md` と skill で表現できないか確認する。

## 検証

- 最小の意味ある検証を先に実行し、必要に応じて full gate の `task ci` を実行する。
- Markdown のみを変更した場合は `task ci:markdown` を優先する。
- frontend 変更では `task ci:typecheck`、`task ci:lint`、`task ci:test`、`task ci:build` を変更範囲に応じて使う。
- Python 変更では `task pytest` または対象 pytest を先に実行する。

## レビュー方針

- review 依頼では、要約より先に重大度順の findings を出す。
- findings は再現可能な根拠、影響、該当ファイル/行を示す。
- 問題が見つからない場合は明確にそう書き、残る検証不足やリスクを短く示す。
- merge 可否は CI、レビュー未解決、AC/DoD、docs、ブランチ状態を確認して判断する。
