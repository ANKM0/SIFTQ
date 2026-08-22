# ADR 0007: Cloudflare D1 を唯一の正本 DB として採用する

## 決定

- task データの唯一の正本 DB として Cloudflare D1 を採用する。
- ブラウザは Worker を経由して D1 を操作し、D1 へ直接アクセスしない。
- SQLite WASM + OPFS は正本に採用しない。

### 決定の理由

- 個人の複数端末から同じ task データを扱うため、共有可能な正本が必要である。
- Worker に認証、所有者確認、入力検証、競合制御を集約できる。

## 不採用

- SQLite WASM + OPFS を正本にする。
  - 複数端末同期を後から追加する必要があり、正本が二重になる。
- クライアントから D1 を直接操作する。
  - 認証・認可・入力検証・競合制御の境界を置けない。

## 補足情報

### 制約事項

- UI は [ADR 0009](0009-adopt-hono-htmx-html-driven-ui.md) に従い、`Browser -> Cloudflare Worker (Hono) -> D1` の経路で実装する。
- 認証、schema、API、オフライン利用、性能最適化は後続の要求または ADR で決定する。

## 参考リンク

- [Cloudflare D1 overview](https://developers.cloudflare.com/d1/)
- [ADR 0009: Hono / HTMX による HTML 駆動 UI を採用する](0009-adopt-hono-htmx-html-driven-ui.md)
