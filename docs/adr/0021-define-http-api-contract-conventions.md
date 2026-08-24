# ADR 0021: Define HTTP API contract conventions

## 決定

- route は名詞・複数形・kebab-case・末尾スラッシュなしを基本とする。
- URL に CRUD 動詞は入れず、カスタム操作だけ例外的に動詞を許容する。
- 検索・絞り込みは query parameter で表現する。
- HTML UI は GET / POST を使い、内部 API は GET / POST / PATCH / DELETE を使う。
- HTML UI の応答は `text/html`、内部 API の要求・応答は `application/json; charset=utf-8`。
- 内部 API の成功レスポンスは GET 200、POST 作成 201 + `Location` + 作成後 task、PATCH 200、DELETE 204、reorder 200 とする。
- API のバージョン管理は行わない。`/api/v1` は使わず `/api` のままにする。

### 決定の理由

- リソース指向 REST（ADR 0020）を一貫した route / method に落とすため。
- 内部 IF は利用側と同じリポジトリで追従できるため、バージョン管理が不要なため。
- HTML form は GET / POST が基本で、HTMX で PUT / PATCH / DELETE を使う必要がないため。

## 不採用

- URL に CRUD 動詞を入れる方式
  - route が操作中心になり、リソース指向と一貫しないため。
- API バージョン管理
  - 外部公開や複数クライアント互換が必要になった時点で再検討する。

## 補足情報

### 背景

- ADR 0018 / 0019 / 0020 の決定を具体的な HTTP 契約として固定する。

### 制約事項

- status / area は `PATCH /api/tasks/{id}`、一括 reorder は `POST /api/tasks/reorder` で表現する。

## 参考リンク

- [Microsoft REST API Guidelines](https://github.com/microsoft/api-guidelines/blob/master/Guidelines.md)
- [Google AIP-122: Resource names](https://google.aip.dev/122)
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
