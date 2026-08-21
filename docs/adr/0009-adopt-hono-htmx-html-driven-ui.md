# ADR 0009: Hono / HTMX による HTML 駆動 UI を採用する

## 決定

- 初期 UI は Cloudflare Worker 上の Hono JSX で HTML を生成する。
- 通常の画面更新は HTMX による部分更新で実装する。
- Drag and drop は SortableJS で即時に表示へ反映し、ドロップ確定時だけ Hono を経由して永続化する。
- React と dnd-kit は初期採用しない。

### 決定の理由

- フォーム、一覧、検索、履歴表示は HTML 駆動で実装できる。
- DnD に必要なクライアント JavaScript を SortableJS に限定し、SPA 全体の状態管理を持ち込まない。
- UI の更新と D1 への書き込みを Worker に集約できる。

## 不採用

- React / dnd-kit を初期 UI にする。
  - DnD 以外の操作までクライアント状態管理を必要としないため。
- 初期から SSR フレームワークや RPC を導入する。
  - HTML の部分更新と通常の HTTP エンドポイントで要件を満たせるため。

## 補足情報

### 背景

- 個人利用から開始し、将来は個人利用者向けに公開する。チーム共同編集は初期要件に含めない。

### 制約事項

- D1 へのアクセスは [ADR 0007](0007-adopt-cloudflare-d1-as-system-of-record.md) に従い、`Browser -> Cloudflare Worker (Hono) -> D1` とする。
- 即時反映する DnD の競合と失敗時の扱いは [ADR 0008](0008-adopt-version-optimistic-locking.md) に従う。
- 認証、オフライン利用、課金、データ保持期間はこの ADR の対象外とする。

## 参考リンク

- [Hono JSX](https://hono.dev/docs/guides/jsx)
- [HTMX documentation](https://htmx.org/docs/)
- [SortableJS documentation](https://sortablejs.github.io/Sortable/)
- [ADR 0007: Cloudflare D1 を唯一の正本 DB として採用する](0007-adopt-cloudflare-d1-as-system-of-record.md)
- [ADR 0008: 更新競合には version 楽観ロックを採用する](0008-adopt-version-optimistic-locking.md)
