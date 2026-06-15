---
codd:
  node_id: design:issue-71-manual-smoke-check
  type: design
  status: draft
---

# Issue #71 手動 smoke check 記録

- 実施日: 2026-06-15
- 対象: `MVP v7: 設定ページを追加する` (`#71`)
- 実施者: Codex (ローカル実行環境)
- 記録先: `Issue #71`（ネットワーク制約のためコメント投稿は未実施）

## 実行結果サマリ

- v7 向け手動 smoke check 手順は `README.md` の `Manual v7 settings smoke check` に反映済み。
- この実行環境では GitHub API への書き込み接続が制限されているため、PR/Issue への直接の実行結果投稿ができなかった。
- UI を伴う手動確認は、実端末で再実行してください。

## 手動確認チェックリスト（未完了）

- [ ] Matrix / Settings 画面で 4 つの matrix area と Done / Skipped のラベルを変更して保存し、反映を確認
- [ ] 空白のみのラベル入力で `Save labels` が無効になることを確認
- [ ] `Restore defaults` で既定ラベルへ戻ることを確認
- [ ] SQLite 接続環境での再起動後復元を確認

