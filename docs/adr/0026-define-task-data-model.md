# ADR 0026: Define task data model

## 決定

- `id` は UUIDv4 とし、`crypto.randomUUID()` で生成する。D1 では TEXT で保持する。
- task に `owner_id` を持たせ、取得・更新の条件に含める。
- `version` は INTEGER、初期値 1、更新成功時に +1。
- `created_at` / `updated_at` は TEXT の ISO 8601 UTC（ミリ秒まで）で保持する。
- `status` / `area` の有効値は `docs/requirements/domain.md` を正とする。D1 では `status` を TEXT、`area` を INTEGER で保持する。
- title の重複可否は domain / README の仕様に従い、D1 では unique 制約を張らない。
- 1 文字は Unicode code point として数える。
- `order` の表示順としての意味は domain に従う。永続化は INTEGER 連番とし、同じ `owner_id + area` 内で `1..N` を保つ。

### 決定の理由

- UUIDv4 は将来の公開・オフライン生成でも推測・衝突に強い。
- `owner_id` を常に条件に含めることで、認証導入後も所有者を分離できる。
- ISO 8601 UTC はタイムゾーン曖昧さがなく、API・DB・画面で扱いやすい。
- title は task の識別子ではないため、重複を禁止しない。
- 連番 order は単純で、個人利用の task 数では batch 正規化のコストが無視できる。

## 不採用

- UUIDv7 だけで timestamp を代替する方式
  - 更新時刻を表現できず、範囲検索や表示が扱いにくいため。
- D1 autoincrement 整数
  - URL / API で連番が推測され、将来の公開時に移行コストが高いため。
- title の unique 制約
  - README の仕様で重複を許可しているため。
- 小数 / fractional indexing による order
  - 精度切れと実装複雑さが増えるため。

## 補足情報

### 背景

- ADR 0007 で D1 を正本、ADR 0008 で version 楽観ロックを採用済み。

### 制約事項

- 認証未実装期間の `owner_id` の固定値 / env 方式は実装時に決める。
- enum の定義場所と表示名の管理方法は実装時に決める。

## 参考リンク

- [ADR 0007: Cloudflare D1 を唯一の正本 DB として採用する](0007-adopt-cloudflare-d1-as-system-of-record.md)
- [ADR 0008: 更新競合には version 楽観ロックを採用する](0008-adopt-version-optimistic-locking.md)
- [RFC 9562: Universally Unique IDentifiers](https://www.rfc-editor.org/rfc/rfc9562.html)
- [RFC 3339: Date and Time on the Internet: Timestamps](https://www.rfc-editor.org/rfc/rfc3339.html)
- [Task Management Domain](../requirements/domain.md)
