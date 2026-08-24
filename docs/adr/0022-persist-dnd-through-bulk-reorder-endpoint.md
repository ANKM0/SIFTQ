# ADR 0022: Persist DnD through bulk reorder endpoint

## 決定

- DnD の永続化は一括 `POST /api/tasks/reorder` に分ける。
- 単体 `PATCH /api/tasks/{id}` の繰り返しで reorder しない。
- reorder の複数行更新は D1 の batch で原子的に処理する。

### 決定の理由

- DnD は複数 task の area / order が同時に変わるため、途中失敗で不整合が残らないようにする。
- 専用 endpoint にすることで rollback と再取得の範囲が明確になる。

## 不採用

- 単体 PATCH の繰り返し
  - 一部成功・一部失敗で order が壊れるため。

## 補足情報

### 背景

- DnD の UI 操作は SortableJS が担当し、ドロップ確定後だけ永続化する。

### 制約事項

- 更新競合は ADR 0008 に従い `409 Conflict` を返す。
- request / response body の詳細は実装時に taqt run artifact で決める。

## 参考リンク

- [ADR 0008: 更新競合には version 楽観ロックを採用する](0008-adopt-version-optimistic-locking.md)
- [Cloudflare D1: D1Database batch()](https://developers.cloudflare.com/d1/worker-api/d1-database/)
