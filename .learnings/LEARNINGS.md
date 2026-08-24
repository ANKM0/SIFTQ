# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | knowledge_gap | best_practice
**Areas**: docs | taqt | frontend | ci | repo
**Statuses**: pending | in_progress | resolved | wont_fix | promoted | promoted_to_skill

## [LRN-20260822-002] correction

**Logged**: 2026-08-22T15:48:00+09:00
**Priority**: medium
**Status**: resolved
**Area**: repo

### Summary
暗号化済み Codex セッションのバックアップ先は private remote に限定せず、公開ブランチへの暗号文 push も利用者の選択肢として扱う。

### Details
公開リポジトリへの暗号文保存を避ける案を優先したが、利用者の意図は公開ブランチへ暗号文を push することだった。設計では暗号化強度、鍵のリポジトリ外保管、公開されるメタデータ、Git 履歴の永続性を明示しつつ、この前提を尊重する。

### Suggested Action
暗号化バックアップの保存先は、利用者が指定する公開・非公開のリモートとし、秘密鍵はリポジトリへ入れない。公開 push を選ぶ場合は recipient 公開鍵のみを追跡し、復号鍵の別経路バックアップを必須とする。

### Metadata
- Source: user_feedback
- Related Files: .learnings/FEATURE_REQUESTS.md
- Tags: codex-session, encryption, git, backup

---

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

## [LRN-20260823-001] knowledge_gap

**Logged**: 2026-08-23T01:25:00+09:00
**Priority**: medium
**Status**: pending
**Area**: taqt

### Summary
deepseek loop の design / test agent は自身の `writes` スコープ外のパス（`scripts/`、`artifacts/` など）へ書くと guard が失敗し、human エスカレーションになる。resume で同じ slice を再実行すれば、design / test がスコープ内だけに触れて完了できる。

### Details
ISSUE-174 の slice 03 / 04 / 06 で、design agent が `scripts/repo_pull_main.py`、`scripts/yoriwake_git_pull.sh`、test agent が worktree root の `artifacts/test-report.md` を書き、`path outside agent write scope` の guard error で loop が human 終端に到達した。実装自体は成功しており、`--resume <run-dir>` で同じ slice を再実行すると design / test は write scope 内のみに変更し、後続 step（implement / observe / checker）が通って done になる。

### Suggested Action
loop の human エスカレーションで guard error が記録されている場合は、ワークスペースの変更を確認した上で `task taqt:run -- <slice> --workspace <worktree> --resume <run-dir>` により再実行する。design / test agent に実装ファイルの作成をさせたい場合は、該当 agent の `writes` にパスを追加してから再実行する。

### Metadata
- Source: error
- Related Files: .taqt/loops/development_feedback_loop_deepseek.yaml, .taqt/scripts/loop/guard.py, .taqt/scripts/taqt/task_run.py
- Tags: taqt, loop, guard, write-scope, resume
- Pattern-Key: taqt.agent_write_scope_guard
- Recurrence-Count: 2
- First-Seen: 2026-08-22
- Last-Seen: 2026-08-23

---

## [LRN-20260823-002] best_practice

**Logged**: 2026-08-23T22:05:00+09:00
**Priority**: high
**Status**: pending
**Area**: taqt

### Summary
taqt の development_feedback_loop は observe で `task ci` 全体ではなく markdown / typecheck / lint / test / build のみ実行するため、`ci:duplicate`（jscpd）や `ci:dead-code`（knip）の失敗が PR の GitHub CI で初めて検出される。

### Details
ISSUE-172 slice 02 で HTMX ビューの属性ブロックが重複し、ローカル taqt run は done 判定になったが、PR の `task ci` が jscpd threshold 0% で失敗した。taqt の observe step 定義（`development_feedback_loop*.yaml`）に `ci:duplicate` / `ci:dead-code`（および `ci:lint:task-refs` / `ci:lint:codex-task-perms`）が含まれていないため、マージ前に手動で `task ci` を通す必要がある。

### Suggested Action
slice の PR を開く前またはマージ前に、worktree で `task ci`（または最低 `ci:duplicate` と `ci:dead-code`）を実行して確認する。恒久対応は observe の run リストに `task ci` を追加するか、taqt ループ定義に不足ゲートを補うこと（issue 172 の対象外のため今回は実施しない）。

### Metadata
- Source: error
- Related Files: .taqt/loops/development_feedback_loop_deepseek.yaml, taskfile/core.yml
- Tags: taqt, loop, ci, jscpd, knip
- Pattern-Key: taqt.loop_observe_gate_gap
- Recurrence-Count: 1
- First-Seen: 2026-08-23
- Last-Seen: 2026-08-23

---
