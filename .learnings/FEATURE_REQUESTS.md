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

