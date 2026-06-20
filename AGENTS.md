# AGENTS.md

## リポジトリ共通ルール

- このリポジトリは SIFTQ の local-first task matrix application である。
- 既存の設計、文書、Taskfile、`.agents/skills/`、`.codex/rules/` を優先する。
- ユーザーの明示指示がある場合を除き、無関係なリファクタリングや履歴整理をしない。
- 既存の未コミット変更はユーザー作業として扱い、明示依頼なしに戻さない。
- 探索は `rg` / `rg --files` を優先し、必要な範囲だけ読む。

## 作業フロー

- Issue 実装や修正では `docs/contributing/development-flow.md` を基準にする。
- branch、commit、PR、merge に関わる作業では `docs/contributing/branch-strategy.md` と `docs/contributing/commit-message-format.md` を確認する。
- requirements、design、wireframes、ADR の扱いが未決なら `.agents/skills/feature-docs-planning/` を使う。
- ADR を作成または更新する場合は `.agents/skills/adr-authoring/` を使う。
- Issue 実装は `.agents/skills/issue-implementation/` を使う。
- 敵対的レビューは `.agents/skills/adversarial-review/` を使う。
- merge 可否の判断は `.agents/skills/merge-readiness/` を使う。
- 再利用できる学びを記録する場合は `.agents/skills/self-improvement/` を使う。

## Codex と自動化

- `.codex/rules/siftq.rules` の command permission rules を尊重する。
- 通常の Codex user config と repository rules を無効化しない。
- `.sympohy/config.yaml` の hooks は sympohy Issue automation の検証層として扱う。
- `sympohy` の生成 worktree と run log は `.sympohy/worktrees/` と `.sympohy/runs/` に置かれる。
- `CLAUDE.md` や role 別の `AGENTS.md` を増やす前に、root `AGENTS.md` と skill で表現できないか確認する。

## 検証

- 最小の意味ある検証を先に実行し、必要に応じて full gate の `task ci` を実行する。
- Markdown のみを変更した場合は `task ci:markdown` を優先する。
- frontend 変更では `task ci:typecheck`、`task ci:lint`、`task ci:test`、`task ci:build` を変更範囲に応じて使う。
- Python/sympohy 変更では `task pytest` または対象 pytest を先に実行し、必要に応じて `task ci:sympohy` を実行する。
- CoDD 文書を変更した場合は `task codd:validate` と必要に応じて `task codd:dag` を実行する。

## レビュー方針

- review 依頼では、要約より先に重大度順の findings を出す。
- findings は再現可能な根拠、影響、該当ファイル/行を示す。
- 問題が見つからない場合は明確にそう書き、残る検証不足やリスクを短く示す。
- merge 可否は CI、レビュー未解決、AC/DoD、docs/ADR/CoDD、ブランチ状態を確認して判断する。
