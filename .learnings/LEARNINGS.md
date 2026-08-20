# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | knowledge_gap | best_practice
**Areas**: docs | taqt | frontend | ci | repo
**Statuses**: pending | in_progress | resolved | wont_fix | promoted | promoted_to_skill

## Status Definitions

| Status | Meaning |
|--------|---------|
| `pending` | Not yet addressed |
| `in_progress` | Actively being worked on |
| `resolved` | Issue fixed or knowledge integrated |
| `wont_fix` | Decided not to address (reason in Resolution) |
| `promoted` | Elevated to AGENTS.md, `.agents/skills/`, `.codex/rules/`, docs, issue templates, or PR templates |
| `promoted_to_skill` | Extracted as a reusable skill |

## Skill Extraction Fields

When a learning is promoted to a skill, add these fields:

```markdown
**Status**: promoted_to_skill
**Skill-Path**: skills/skill-name
```

Example:
```markdown
## [LRN-20250115-001] best_practice

**Logged**: 2025-01-15T10:00:00Z
**Priority**: high
**Status**: promoted_to_skill
**Skill-Path**: skills/docker-m1-fixes
**Area**: ci

### Summary
Docker build fails on Apple Silicon due to platform mismatch
...
```

## [LRN-20260820-001] correction

**Logged**: 2026-08-20T22:49:00+09:00
**Priority**: medium
**Status**: pending
**Area**: repo

### Summary
反復する失敗への昇格先である「task」は GitHub Task ではなく Taskfile の `task` コマンドを指す。

### Details
セッションログから反復するコマンド失敗を検出した場合、再現可能な操作を `Taskfile.yml` / `taskfile/` に Task として集約する。GitHub Issue や taqt task の作成を意味すると解釈しない。

### Suggested Action
自己改善の集計・昇格ルールでは、反復失敗を `task <name>` にする候補として扱う。Taskfile に追加した場合は、既存の `ci:lint:task-refs` と `ci:lint:codex-task-perms` を通す。

### Metadata
- Source: user_feedback
- Related Files: Taskfile.yml, taskfile/core.yml, .agents/skills/self-improvement/SKILL.md
- Tags: taskfile, recurring-failure, command

---
