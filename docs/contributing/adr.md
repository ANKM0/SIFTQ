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
