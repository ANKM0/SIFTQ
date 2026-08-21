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

## [LRN-20260820-002] correction

**Logged**: 2026-08-20T23:15:00+09:00
**Priority**: medium
**Status**: resolved
**Area**: ci

### Summary
品質ゲートの導入方針は、既存の違反・実装の有無を確認してから基準凍結の要否を決める。

### Details
新規実装のみのリスタートであるにもかかわらず、既存のlint負債を凍結して新規違反だけを止める段階的導入を提案した。既存実装がない場合は基準凍結を作らず、初日からESLint・型検査・テスト・build・品質検査の全違反をCIで停止する。

### Suggested Action
導入提案では、品質基準を緩和する前に既存コードと違反の有無を明示的に確認する。

### Metadata
- Source: user_feedback
- Related Files: eslint.config.js, tsconfig.json, taskfile/core.yml, .github/workflows/ci.yml
- Tags: quality-gate, baseline, greenfield

---

## [LRN-20260821-001] correction

**Logged**: 2026-08-21T00:00:00+09:00
**Priority**: low
**Status**: resolved
**Area**: ci

### Summary
ツールチェーン選定では、利用者の「仕組みを減らす」という基準だけで統合ツールを除外せず、設定・フック・品質コマンドの集約効果も比較する。

### Details
Bun と Vite+ の役割重複を理由に Vite+ を早期に除外した。しかし Vite+ は Vite、Oxlint、Oxfmt、テスト、staged-file checks と設定を集約できるため、個人開発で複数ツールを個別接続するより軽量になる場合がある。Bun を優先する根拠は、Vite+ が Node.js とパッケージマネージャを管理する点との方針衝突であり、単なる重複ではない。

### Suggested Action
選定時は、実行時・パッケージ管理・品質ゲート・設定ファイルの所有者を表にして、利用者の優先順位に沿って判断する。

### Metadata
- Source: user_feedback
- Related Files: .learnings/LEARNINGS.md
- Tags: toolchain, vite-plus, bun, architecture

---
