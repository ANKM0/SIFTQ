# Errors

Command failures, API errors, and unexpected behavior captured during development.

**Areas**: docs | taqt | frontend | ci | repo
**Statuses**: pending | in_progress | resolved | wont_fix | promoted | promoted_to_skill

## Status Definitions

| Status | Meaning |
|--------|---------|
| `pending` | Not yet addressed |
| `in_progress` | Actively being worked on |
| `resolved` | Issue fixed (add Resolution block) |
| `wont_fix` | Decided not to address (reason in Resolution) |
| `promoted` | Elevated to AGENTS.md, `.agents/skills/`, `.codex/rules/`, docs, issue templates, or PR templates |
| `promoted_to_skill` | Extracted as a reusable skill |

Entry format: see the self-improvement skill's "Error Entry" section. IDs use `ERR-YYYYMMDD-XXX`.

---

## [ERR-20260904-002] taqt_opencode_recursive_schema

**Logged**: 2026-09-04T22:00:00+09:00
**Priority**: medium
**Status**: pending
**Area**: taqt

### Summary
taqt の実装エージェントが OpenCode provider の再帰 JSON schema 非対応で停止した。

### Error
```
Recursive JSON schemas are not currently supported
```

### Context
- Issue #302 slice 02 の `implement` step で発生。
- 既存実装の検証は完了していたため、対象差分への影響はなかった。

### Suggested Fix
taqt profile の provider schema 互換性を事前検証し、非対応 provider の場合は互換モデルへ fallback する。

### Metadata
- Reproducible: unknown
- Related Files: .taqt/config/profiles.yaml, .taqt/scripts/loop/llm.py

---

## [ERR-20260904-001] taqt_unapproved_aqua_policy_in_worktree

**Logged**: 2026-09-04T21:14:43+09:00
**Priority**: medium
**Status**: pending
**Area**: taqt

### Summary
新規 taqt worktree の `aqua-policy.yaml` が未承認で、taqt が起動する Codex が実行前に停止する。

### Error
```
this package isn't allowed
```

### Context
- `task taqt:run` を Issue #327 の worktree で実行した。
- Issue #322 の run にも同じ aqua policy 未承認エラーがある。

### Suggested Fix
worktree 作成時に `aqua policy allow` を実行するか、taqt 実行前チェックで未承認 policy を検出して承認手順を案内する。

### Metadata
- Reproducible: yes
- Related Files: .taqt/scripts/taqt/git_worktree.py, .taqt/scripts/taqt/task_run.py

---

## [ERR-20260906-002] taqt_verification_package_version_baseline

**Logged**: 2026-09-06T15:52:21+09:00
**Priority**: medium
**Status**: pending
**Area**: taqt

### Summary
taqtの検証が、変更と無関係なpackage.jsonのバージョン不一致で停止した。

### Error
```
package.json version is older than the latest release tag: 0.6.2 < 0.7.3
```

### Context
- Issue #355 slice 01のverificationで`task ci:lint:python`を実行した。
- `ruff check`は成功したが、既存のpackage version checkが失敗した。
- UI変更の対象テスト、typecheck、build、lintは別途成功した。

### Suggested Fix
taqtのverificationで変更と無関係な既知のベースライン失敗を識別し、対象変更の検証結果と分けて扱えるようにする。

### Metadata
- Reproducible: yes
- Related Files: scripts/ci/check_package_version.py, taskfile/ci.yml
- See Also: ERR-20260904-001

---
