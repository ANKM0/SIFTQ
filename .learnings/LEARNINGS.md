# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | knowledge_gap | best_practice
**Areas**: docs | taqt | frontend | ci | repo
**Statuses**: pending | in_progress | resolved | wont_fix | promoted | promoted_to_skill

## [LRN-20260830-003] correction

**Logged**: 2026-08-30T16:05:00+09:00
**Priority**: high
**Status**: pending
**Area**: repo

### Summary
複数Issueで進める作業は、子IssueのPRをmainへ直接マージせず、親Issueブランチへ統合する。

### Details
#245のPRをmain向けに作成したが、利用者は修正中の後続Issueをmainへ流入させないため、親Issueブランチをmainから作成し、子IssueのPRをそこへ順に統合する方針を指定した。

### Suggested Action
複数Issueを段階的に統合する作業では、PR作成前に親Issue番号・統合ブランチ・最終的なmainへのマージ条件を確認する。

### Metadata
- Source: user_feedback
- Related Files: docs/contributing/branch-strategy.md, .github/pull_request_template.md
- Tags: branching, parent-issue, integration, pull-request

---

## [LRN-20260830-002] correction

**Logged**: 2026-08-30T01:18:00+09:00
**Priority**: medium
**Status**: resolved
**Area**: repo

### Summary
移行手順の依頼では、進捗記録ではなく指定された作業を実施する。

### Details
利用者がモックBE付きFEプレビューへの移行を開始し「まず1から」と指示した際、差分の分類を文書へ追記するだけで、次に求められる差分復元を実施しなかった。進捗は必要最小限のチェック更新に留め、明示された作業を完了させる。

### Suggested Action
段階的な移行指示では、対象ステップの実作業と検証を先に行い、文書はチェック状態だけ更新する。

### Metadata
- Source: user_feedback
- Related Files: 不満点.md, src/, tests/
- Tags: migration, execution, progress

### Resolution
- **Resolved**: 2026-08-30T01:18:00+09:00
- **Notes**: `src/`・`tests/` の対象差分を復元し、進捗記録をチェック状態へ整理する。

---

## [LRN-20260822-002] correction

**Logged**: 2026-08-22T15:48:00+09:00
**Priority**: medium
**Status**: in_progress
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

## [LRN-20260830-001] correction

**Logged**: 2026-08-30T00:18:00+09:00
**Priority**: medium
**Status**: resolved
**Area**: docs

### Summary
wireframe の設計変更では、実アプリの `src/` を変更せず、生成スクリプトと `docs/wireframes` に限定する。

### Details
wireframe の状態・共通レイアウトを表現する依頼に対して、実アプリの `src/` とアプリテストを変更してしまった。今回の目的は実装変更ではなく、wireframe 専用の設計案を作ることだった。

### Suggested Action
wireframe の依頼では、先に `scripts/generate-wireframes.ts` が実装追従用か設計案用かを確認する。設計案の場合は wireframe 専用テンプレート、状態定義、CSS 上書き、README に変更を限定する。

### Metadata
- Source: user_feedback
- Related Files: scripts/generate-wireframes.ts, docs/wireframes/README.md, src/index.tsx
- Tags: wireframe, scope, source-of-truth

### Resolution
- **Resolved**: 2026-08-30T00:18:00+09:00
- **Notes**: `src/` の変更を戻し、wireframe 専用の生成処理へ切り替えた。

---

## [LRN-20260829-001] correction

**Logged**: 2026-08-29T20:15:00+09:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
Matrix の「area を押下」は area 番号ではなく、各象限の section 全体を指していた。

### Details
area 見出しへのリンクだけを実装したため、利用者が指定した Matrix の section 要素を
押下しても新規タスク作成へ遷移しなかった。画面上の対象範囲が曖昧な場合、DOM 指定や
操作対象の範囲を確認してから実装する。

### Suggested Action
Matrix の各 area section の余白クリックを新規作成へ遷移させ、task card と DnD 操作を
除外する。操作対象を示すE2EまたはUIテストを追加する。

### Metadata
- Source: user_feedback
- Related Files: src/index.tsx, src/components/Layout.tsx, tests/bdd/task-ui.contract.test.ts
- Tags: frontend, matrix, area, click-target, wireframe

### Resolution
- **Resolved**: 2026-08-29T20:45:00+09:00
- **Notes**: quadrant section の空白クリックを area 付き新規作成へ遷移させ、カードと DnD を前面へ分離した。

---

## [LRN-20260829-002] correction

**Logged**: 2026-08-29T20:50:00+09:00
**Priority**: low
**Status**: resolved
**Area**: frontend

### Summary
クリック領域を実装するための視覚的な案内文・点線は、要件に含まれなかった。

### Details
area section 全体のクリックを実現する際に、案内文と点線枠を追加したが、利用者は
画面へ追加の表示を求めていなかった。操作可能領域の実装と視覚的な補助表示を分けて判断する。

### Suggested Action
要件にない説明文・装飾を追加する前に、既存の画面密度や明示的な要望を確認する。

### Metadata
- Source: user_feedback
- Related Files: src/index.tsx, src/styles.ts
- Tags: frontend, wireframe, scope, visual-design
- See Also: LRN-20260829-001

### Resolution
- **Resolved**: 2026-08-29T20:50:00+09:00
- **Notes**: 透明なクリック領域だけを残し、案内文と点線を削除した。

---

## [LRN-20260829-006] correction

**Logged**: 2026-08-29T21:20:00+09:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
同じStatus/Areaポップオーバーを持つ画面は、見た目とchoice定義を共通コンポーネントにする。

### Details
New task用にnative detailsの別UIを追加したため、Detailのpopoverと表示が乖離した。

### Suggested Action
画面間で同じ操作・見た目が必要な場合は、状態更新方法だけを注入し、描画構造とchoice定義を共通化する。

### Metadata
- Source: user_feedback
- Related Files: src/components/TaskMetaPopover.tsx, src/components/OptionMenu.tsx, src/index.tsx
- Tags: frontend, component, popover, reuse

### Resolution
- **Resolved**: 2026-08-29T21:20:00+09:00
- **Notes**: TaskMetaPopoverに共有し、DetailはHTMX、新規作成はform radioで利用した。


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

同じ問題は ISSUE-336 slice 01（`ci:lint:ts-fast` 削除）でも発生した。新規 run では `taskfile/ci.yml` に加えて `.codex/rules/siftq.rules` と `.taqt/scripts/loop/verification.py` まで scope 外編集が拡大したため、単純なリランではなく resume を先に試す必要がある。infra 系では design 成果物と実装ファイルの境界が曖昧になりやすい。

### Suggested Action
loop の human エスカレーションで guard error が記録されている場合は、ワークスペースの変更を確認した上で `task taqt:run -- <slice> --workspace <worktree> --resume <run-dir>` を先に試す。再発する場合は agent の `writes` を拡張するか手動実装へ切り替える。design agent が `.taqt/scripts/` など loop 自身のファイルを変更した場合は、内容の正否に関わらず revert してから次の手段を選ぶ。

### Metadata
- Source: error
- Related Files: .taqt/loops/development_feedback_loop_deepseek.yaml, .taqt/loops/main_loop.yaml, .taqt/scripts/loop/guard.py, .taqt/scripts/loop/verification.py, .taqt/scripts/taqt/task_run.py, .codex/rules/siftq.rules, taskfile/ci.yml
- Tags: taqt, loop, guard, write-scope, resume
- Pattern-Key: taqt.agent_write_scope_guard
- Recurrence-Count: 3
- First-Seen: 2026-08-22
- Last-Seen: 2026-09-04

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
