# ADR 0007: Cloudflare D1 を唯一の正本 DB として採用する

## 決定

- task データの唯一の正本 DB として Cloudflare D1 を採用する。
- クライアントから D1 を直接操作せず、`React SPA -> Cloudflare Worker -> D1` の経路にする。
- SQLite WASM + OPFS は正本に採用しない。オフライン利用が必要になった場合だけ、ローカルキャッシュとして再評価する。
- Read Replication は、計測で読み取りのレイテンシまたはスループットが課題になった時点で有効化する。利用時は Sessions API を必須とし、更新直後に最新状態が必要な読み取りは primary を使う。

### 決定の理由

- 個人の複数端末から同じ task データを扱うため、共有可能な正本が必要である。
- D1 は SQLite セマンティクスを持ち、複数更新を原子的に実行できる。
- ブラウザ内 DB を正本にすると、D1 導入時に同期、競合解決、移行を別途実装する必要がある。
- Worker に認証、所有者確認、入力検証、競合制御を集約できる。

## 不採用

- SQLite WASM + OPFS を正本にする。
  - 複数端末同期を後から追加する必要があり、正本が二重になる。
- クライアントから D1 を直接操作する。
  - 認証・認可・入力検証・競合制御の境界を置けない。

## 補足情報

### 背景

- パフォーマンスと ACID 特性を優先する。
- 将来、複数端末から task をほぼ自動で同期する。

### 制約事項

- D1 の更新は primary に集約される。Read Replication は読み取りだけを高速化する。
- 認証、schema、API、オフライン時の振る舞いは後続の Design Doc で決定する。

## 参考リンク

- [Cloudflare D1 overview](https://developers.cloudflare.com/d1/)
- [Cloudflare D1 global read replication](https://developers.cloudflare.com/d1/best-practices/read-replication/)
