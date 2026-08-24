# ADR 0023: Adopt RFC 9457 error body

## 決定

- JSON endpoint のエラー body は RFC 9457 Problem Details を採用する。
- プログラム用 `code` と人間向け `title` / `detail` を分ける。
- 入力検証エラーは `errors` 拡張で項目単位に返す。

### 決定の理由

- 独自形式を作らず、標準のエラー形式を再利用できる。
- クライアントは message 文字列ではなく `code` で分岐でき、文言変更や国際化に強くなる。

## 不採用

- 独自の `{ message }` 形式
  - クライアントが文字列マッチに依存し、分岐が壊れやすいため。

## 補足情報

### 背景

- 内部 API でも機械可読なエラー契約が必要。

### 制約事項

- クライアントは `title` / `detail` の文字列で分岐しない。
- HTML UI は JSON を返さず、エラー fragment を返す。

## 参考リンク

- [RFC 9457: Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html)
- [Google AIP-193: Errors](https://google.aip.dev/193)
