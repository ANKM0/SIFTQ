# AGENTS.md

## 共通

- 文章は簡潔かつ必要十分にし、削れる語は削る。
- Python は `>=3.11` を前提とし、`from __future__ import annotations` は記載しない。
- ユーザーの明示指示がある場合を除き、無関係なリファクタリングや履歴整理をしない。
- 既存の未コミット変更はユーザー作業として扱い、明示依頼なしに戻さない。
- 探索は `rg` / `rg --files` を優先し、必要な範囲だけ読む。
- 既存の設計、文書、Taskfile、`.codex/rules/` を優先する。

## 検証

- 検証コマンドの正は Taskfile、CI、hook に置く。
- 変更範囲に対して最小の意味ある検証を実行する。

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
