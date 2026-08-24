# ADR 0018: Adopt HTML-driven UI with JSON only for DnD

## 決定

- 画面表示・画面遷移・フォームは Hono JSX + HTMX の HTML 駆動で実装する。
- JSON endpoint は DnD のドロップ確定時のみ使う。
- 通常操作で SPA 全体の状態管理は持たない。

### 決定の理由

- ADR 0009 が HTML 駆動 UI を採用しているため。
- フォーム・一覧・詳細はサーバー生成 HTML の部分更新で要件を満たせるため。
- DnD だけは即時反映と rollback を SortableJS 側で扱う必要があるため、永続化を JSON に限定する。

## 不採用

- 画面・フォームを JSON で更新する SPA 方式
  - 通常操作までクライアント状態管理が増えるため。
- すべてを JSON で統一する方式
  - HTML 駆動 UI の利点を失うため。

## 補足情報

### 背景

- Issue #172 で React SPA を Hono / HTMX / SortableJS へ移行する。
- HTML と JSON の境界を明確にし、endpoint 設計の前提を作る。

### 制約事項

- UI スタックは ADR 0009 に従う。
- DnD の永続化 endpoint とレスポンス形式は ADR 0022 で定める。

## 参考リンク

- [ADR 0009: Hono / HTMX による HTML 駆動 UI を採用する](0009-adopt-hono-htmx-html-driven-ui.md)
- [htmx Documentation](https://htmx.org/docs/)
