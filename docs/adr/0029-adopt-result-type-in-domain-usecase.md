# ADR 0029: Adopt Result type in domain and usecase

## 決定

- domain / usecase は期待される失敗を `Result<T, E>` で返す。
- `Result` は次の inline union とする。

```ts
type Result<T, E> =
  | { ok: true; value: T }
  | { ok: false; error: E };
```

- helper は `ok()` / `err()` と、必要最小限の合成関数だけ用意する。
- domain error は `code` を持つ discriminated union とし、`Error` 継承を必須にしない。
- 予期せぬ例外は `throw` のままにし、最上位で 500 に変換する。

### 決定の理由

- 期待される失敗を型として扱い、presentation 層で HTTP status / RFC 9457 へ変換しやすくする。
- inline union は定義が短く、TypeScript の一般的なパターンで扱いやすい。
- 例外を制御フローに使わないことで、エラー分岐を明示できる。

## 不採用

- 全エラーを例外で扱う方式
  - 期待される失敗まで例外制御になり、型でエラーを追跡できないため。
- `neverthrow` / `fp-ts` / `effect` の導入
  - 抽象化と依存が増えるため、最小の `Result` 自作で十分。
- 副作用までモナドで包む方式
  - TypeScript で記述量が増え、読みやすさを損なうため。

## 補足情報

### 背景

- ADR 0006 の軽量アーキテクチャで、domain と入出力を分離する。
- ADR 0023 / 0024 / 0025 のエラー方針と整合させる。

### 制約事項

- domain / usecase は HTTP や HTML に依存しない。
- `DomainError` は `code` を持ち、presentation 層で status + body に変換する。
- `Promise<Result<T, E>>` は repository の戻り値として使う。

## 参考リンク

- [ADR 0006: アーキテクチャとして、軽量アプリケーションアーキテクチャを採用する](0006-adopt-lightweight-application-architecture.md)
- [ADR 0023: Adopt RFC 9457 error body](0023-adopt-rfc9457-error-body.md)
- [ADR 0024: Map errors to standard HTTP status codes](0024-map-errors-to-standard-http-status-codes.md)
- [ADR 0025: Define HTML and JSON error handling behavior](0025-define-html-and-json-error-handling-behavior.md)
