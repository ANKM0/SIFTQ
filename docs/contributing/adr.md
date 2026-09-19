# ADR

## 目的

意思決定の理由 (Why) を残す。

## 手順

- Path: `docs/adr/<four-digit-number>-<decision-title-in-kebab-case>.md`
- Template: `.agents/templates/adr.md`
- Script: `uv run python scripts/create_adr.py --title "..." --slug "..." --dry-run`

1. 次の 4 桁番号を採番する。
1. template の placeholder を埋める。
1. `docs/adr/README.md` に追加する。

## レビュー

- 実装詳細が混ざっていないかを確認する。ADR には意思決定のみを書き、識別子・設定値・処理順序・コード・コマンド・source path は code か design doc に置く。
- 決定論チェック: `task -t .config/Taskfile.yml ci:adr`（新規採番 ADR のコードフェンスと source path を検出）。
- 散文レビュー: `adr-review` skill（LLM）で実装詳細を列挙し、`changes_requested` の指摘を解消する。

## 更新

- 既に Accepted の ADR は本文を書き換えない。`> Status: Superseded by [ADR XXXX](...).` を先頭に付し、新しい決定を新規 ADR として起こす。
