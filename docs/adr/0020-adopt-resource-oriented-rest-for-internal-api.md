# ADR 0020: Adopt resource-oriented REST for internal API

## 決定

- 内部 API はリソースごとの REST API として設計する。
- BFF、RPC、GraphQL は採用しない。

### 決定の理由

- CLI と将来のクライアントが task の CRUD を同じ契約で使える。
- CRUD 中心の要件では、リソース指向 REST が最も単純で予測しやすい。
- Web UI は HTML 駆動で JSON API を消費しないため、BFF が不要。

## 不採用

- BFF
  - クライアント別のレスポンス最適化が必要ないため。
- GraphQL
  - 取得形の自由度やリアルタイム性が必要ないため。
- Hono RPC / RPC
  - HTMX 主体では型共有の利点が小さく、通常の HTTP endpoint で十分なため。

## 補足情報

### 背景

- API は非公開（ADR 0019）だが、将来の CLI が同じ内部 API を使う。

### 制約事項

- route 命名と method の詳細は ADR 0021 に従う。

## 参考リンク

- [Fielding: Architectural Styles and the Design of Network-based Software Architectures](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm)
- [Google AIP-121: Resource-oriented design](https://google.aip.dev/121)
- [Hono RPC](https://hono.dev/docs/guides/rpc)
