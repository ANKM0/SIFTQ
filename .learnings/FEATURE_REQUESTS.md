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

## [FEAT-20260822-001] encrypted-codex-session-backup

**Logged**: 2026-08-22T15:38:00+09:00
**Priority**: high
**Status**: pending
**Area**: repo

### Requested Capability
Codex のローカル生セッションをクライアント側で暗号化し、このリポジトリへコミットしてリモートへ同期する。

### User Context
PC 障害時にも、ローカルのセッション全記録を復元できるようにし、LLM が過去の会話を必要時に振り返って改善へ役立てられるようにする。

### Complexity Estimate
medium

### Suggested Implementation
平文を作業ツリーへ書き込まず、完了したセッションごとに zstd 圧縮してから age などの公開鍵暗号で暗号化し、専用ディレクトリへ `.jsonl.zst.age` として出力する。秘密鍵はリポジトリ外かつ別経路で保管する。暗号化アーカイブを必要時に局所復号・検索する仕組み、定期同期スクリプト、復元手順を追加する。

### Metadata
- Frequency: first_time
- Related Features: session-driven-self-improvement

---

## [FEAT-20260829-001] task-editor-draft-and-stateful-wireframes

**Logged**: 2026-08-29T21:44:00+09:00
**Priority**: medium
**Status**: in_progress
**Area**: frontend

### Requested Capability
新規タスクを Create するまで DB へ保存しない画面内下書きと、押下対象ごとの状態・遷移先を表す wireframe を提供する。

### User Context
新規作成と詳細編集を共通の編集画面として確認しつつ、リロード時には新規作成中の変更を初期値へ戻したい。

### Complexity Estimate
medium

### Suggested Implementation
new 側の Status／Area は form に紐付く画面内状態として保持し、Create 時だけ POST する。共通編集画面を導入し、new は Create、detail は Save を設定で切り替える。wireframe generator は各リンク・ポップアップ・選択状態を個別ページとして出力する。

### Metadata
- Frequency: first_time
- Related Features: wireframe-preview, task-editor

---
