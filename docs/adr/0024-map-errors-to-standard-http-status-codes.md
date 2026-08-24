# ADR 0024: Map errors to standard HTTP status codes

## 決定

- エラーは標準 HTTP ステータスコードにマップする。
- 入力検証 400、認証 401、権限 403、不在 404、競合 409、予期せぬエラー 500。
- HTTP ステータスは大分類、body の `code` は詳細分類として使う。
- カスタム HTTP ステータスコードは作らない。
- エラーを 200 で返さない。

### 決定の理由

- 汎用クライアントや proxy が理解できる標準コードに寄せるため。
- 詳細なエラー種別は status ではなく RFC 9457 の `code` で表現するため。

## 不採用

- カスタム HTTP ステータスコード
  - 中間装置や汎用クライアントが解釈できないため。
- 200 で body の code だけ変えてエラーを返す方式
  - エラーを成功として扱う誤解を招くため。

## 補足情報

### 背景

- ADR 0008 で競合は 409 と決定済み。

### 制約事項

- 401 / 403 は認証未実装でも共通仕様として定義する。

## 参考リンク

- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
- [MDN: HTTP response status codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status)
