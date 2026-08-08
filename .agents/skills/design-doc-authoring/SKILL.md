---
name: design-doc-authoring
description: Create or update SIFTQ Design Docs for feature-level design, implementation approach, workflow, UI, data, or API decisions.
---

# Design Doc Authoring

Use this skill when creating or updating a SIFTQ Design Doc.

## Flow

1. Read `docs/design/README.md`.
2. Decide PR number, title, and scope.
3. Write purpose, goals, non-goals, background, constraints, solved problems, proposed design, rejected options, impact, validation plan, unresolved questions, and references.
4. Use `scripts/create_design_doc.py` for path and template copy.
5. Update `docs/design/README.md`.
6. If the Design Doc creates a cross-cutting architecture or tooling decision, create an ADR and link it.

## 作成手順

```bash
uv run python scripts/create_design_doc.py --pr 123 --title "..." --dry-run
```

- Path: `docs/design/#<pr-number>.md`
- Template: `docs/design/templates/design-doc.md`
- Script: `uv run python scripts/create_design_doc.py --pr 123 --title "..." --dry-run`

1. PR ごとに 1 つ Design Doc を作る。
1. ファイル名は PR 番号に合わせる。
1. template のコメントに沿って内容を書く。
1. `docs/design/README.md` の一覧に追加する。
1. README から `#<pr-number>.md` にリンクする場合は、`[#123](%23123.md)` のように `#` を `%23` として書く。
1. 関連する requirements、wireframes、Issue、ADR があればリンクする。

## Writing Rules

- Keep it concise.
- Link related requirements, wireframes, issues, PRs, and ADRs.
- Keep AC / DoD in the issue, not in the Design Doc.
- State non-goals so the scope is reviewable.
- Include only meaningful rejected options.
- Prefer `なし` for empty sections over deleting required headings.
