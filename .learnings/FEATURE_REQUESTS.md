# Feature Requests

Missing capabilities requested by users, captured during development.

**Areas**: docs | taqt | frontend | ci | repo
**Statuses**: pending | in_progress | resolved | wont_fix
**Complexity**: simple | medium | complex

## Status Definitions

| Status | Meaning |
|--------|---------|
| `pending` | Not yet addressed |
| `in_progress` | Actively being built |
| `resolved` | Capability implemented (add Resolution block) |
| `wont_fix` | Decided not to build (reason in Resolution) |

Entry format: see the self-improvement skill's "Feature Request Entry" section. IDs use `FEAT-YYYYMMDD-XXX`.

---

## [FEAT-20260820-001] session-driven-self-improvement

**Logged**: 2026-08-20T22:55:00+09:00
**Priority**: high
**Status**: pending
**Area**: repo

### Requested Capability
Codex のローカルセッションを自動集計し、反復するコマンド失敗やユーザー訂正を検知して、改善候補の GitHub Issue を自動作成する。

### User Context
反復失敗は Taskfile の `task` コマンドへ、反復指摘は rule または skill へ昇格し、同じ失敗を減らしたい。

### Complexity Estimate
complex

### Suggested Implementation
Codex session を repository / worktree 単位で走査し、候補を `.learnings/` に証跡付きで蓄積する。3回・2タスク・30日以内の昇格条件を満たした候補だけを GitHub Issue として idempotent に作成する。Issue 作成後の Taskfile・rule・skill 変更は既存 taqt workflow で実施する。

### Metadata
- Frequency: first_time
- Related Features: self-improvement, taqt:self-improvement, taqt:watch

---
