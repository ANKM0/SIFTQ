# ADR 0025: Define HTML and JSON error handling behavior

## 決定

- 内部エラー型と HTTP status への変換は共通化する。
- JSON API は RFC 9457、HTML UI はエラー用 HTML fragment を返す。
- HTML UI に JSON を返さず、JSON API に HTML を返さない。
- HTMX では `HX-Retarget` / `HX-Reswap` を共通処理として使う。
- サーバー内部エラーの詳細は client に返さず、ログにだけ残す。
- 401 はログイン / 再認証へ誘導し、403 は権限エラーを表示してログインへ戻さない。
- API のエラーテストは HTTP status + body の `code` を検証し、message 文字列を検証しない。

### 決定の理由

- エラーの意味（status / code）を共通にし、表現だけ HTML / JSON で分ける。
- スタックトレースや SQL、D1 内部エラーを client に露出しない。
- 403 を 401 と同様に扱うと再ログインしても権限がないループに入るため。
- 文言変更でテストや分岐が壊れないようにする。

## 不採用

- 内部エラー詳細の client への露出
  - 情報漏えいと実装詳細の露出を招くため。
- 403 をログイン画面へリダイレクト
  - 再認証では解決しないため。
- message 文字列によるエラーテスト
  - 文言変更で壊れるため。

## 補足情報

### 背景

- HTML UI と JSON API の両方で一貫したエラー処理が必要。

### 制約事項

- エラー body は ADR 0023、status code は ADR 0024 に従う。
- 認証は今回実装しないが、401 / 403 の共通挙動だけ先に定義する。

## 参考リンク

- [htmx: Response Headers](https://htmx.org/reference/#response_headers)
- [MDN: HTTP authentication](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Authentication)
