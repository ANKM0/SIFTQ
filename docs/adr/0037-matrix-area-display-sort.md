# ADR 0037: Matrix area display sort

## 決定

- Matrix に area 内の表示専用ソートを導入する。ソートはカードの表示順だけを変え、task の `area` と永続 `order` は変更しない。
- ソートはサーバー側（HTML 駆動）で行い、`GET /` の query param `sort` で指定する。HTMX で Matrix を再描画する。
- ソート key は `order`（既定）、`title`、`created_at`、`updated_at` とする。`order` は既存表示を維持する。

### 決定の理由

- HTML 駆動 UI（ADR 0009）に合わせ、新しい client script を増やさずサーバーで並べ替える。
- 表示専用にすることで、DnD が管理する永続 `order` を壊さない。

## 不採用

- client side sort（JS で DOM を並べ替え）
  - ADR 0018 の「JSON は DnD のみ」方針から外れ、DnD の order 計算とも競合しやすいため。
- `order` を書き換える永続ソート
  - 親 issue の Scope 外（永続順序モデル変更）であり、DnD の競合も増えるため。

## 補足情報

### 背景

- area に表示領域を超える数の `do` タスクがあると、カードが見切れて全タスクを確認できない。

### 制約事項

- sort の対象は `do` タスクのみ（Matrix は `do` のみ表示する）。
- sort 中も各タスクは元の area に留まる。カードの遷移と drag and drop は引き続き利用できる。
- sort key の昇順/降順と UI コントロールの配置は実装で確定する。

## 参考リンク

- [ADR 0009: Hono / HTMX による HTML 駆動 UI を採用する](0009-adopt-hono-htmx-html-driven-ui.md)
- [ADR 0018: Adopt HTML-driven UI with JSON only for DnD](0018-adopt-html-driven-ui-with-json-only-for-dnd.md)
- [Task Management Screens](../requirements/screens.md)
