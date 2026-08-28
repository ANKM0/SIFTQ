# AGENTS.md

## 共通

- 文章は簡潔かつ必要十分にし、削れる語は削る。
- 文章と段落はそれぞれ一つの責務に絞る。結論、理由、制約、次の行動を同じ段落に混在させず、同じ説明を別節で繰り返さない。
- Python は `>=3.11` を前提とし、`from __future__ import annotations` は記載しない。
- ユーザーの明示指示がある場合を除き、無関係なリファクタリングや履歴整理をしない。
- 既存の未コミット変更はユーザー作業として扱い、明示依頼なしに戻さない。
- 調査・判断・計画のみの依頼では原則ファイル変更・実装をしない。実装指示が明示されるまで編集しない。判断だけの依頼では、変更前に完了条件とスコープを確認する。
- 探索は `rg` / `rg --files` を優先し、必要な範囲だけ読む。`rg` が無い環境では `find` / `grep` へ即フォールバックする。
- 既存の設計、文書、Taskfile、`.codex/rules/` を優先する。

## 検証

- 検証コマンドの正は Taskfile、CI、hook に置く。
- 変更範囲に対して最小の意味ある検証を実行する。

## AI 実装の品質

- `any`、non-null assertion、型アサーション、lint 無効化で型・lint の失敗を回避しない。設計または型ガードで直す。
- 例外は設定ファイルに対象を限定し、理由と削除条件を記す。インラインの無効化コメントは追加しない。
- ロジックを追加・変更したら、同時にテストを追加・更新する。入出力規則は副作用から分離し、pure 関数としてテスト可能にする。
- 新しい共通 helper を作る前に既存実装を検索し、知識の重複を作らない。

## DeepSeek 利用コスト

- 長大タスクはサブタスク単位でセッションを分割し、1 セッションへ履歴を蓄積しない。
- コマンド・ツール出力は必要最小限に絞り、`rg` / `head` / `sed -n` で必要な範囲だけ読む。
- 定型・軽量な実装は flash を使い、pro は設計・重要レビューに限定する。

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
