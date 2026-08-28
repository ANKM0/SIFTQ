# ADR 0032: Adopt Worker-managed shared-password authentication

## 決定

- `siftq` Worker のアクセス制御は、Cloudflare Access ではなく Worker 内の共有パスワード認証で行う。
- パスワードとセッション署名鍵は Wrangler Secrets（`AUTH_PASSWORD` / `SESSION_SECRET`）で管理する。
- ログイン成功時に署名付き HttpOnly Cookie を発行し、middleware で全 HTML / API を保護する。

### 決定の理由

- Cloudflare Zero Trust の有効化・設定が不要で、Worker 単体で完結する。
- 個人利用では共有パスワード 1 つで十分で、既存の Hono 構成に最小のコードで追加できる。
- 将来ユーザー別に拡張する場合も、Cookie セッションと `owner_id` の分離へ発展させられる。

## 不採用

- Cloudflare Access（Cloudflare Zero Trust）
  - Zero Trust の onboarding とポリシー設定が必要で、個人利用には導入コストが上回るため。
  - ADR 0031 を supersede する。
- HTTP Basic 認証
  - 実装は最小だが、明示的なログアウトがなく UX が劣るため。
- IP 制限
  - モバイルや家庭回線では IP が変わり、運用できないため。

## 補足情報

### 背景

- `*.workers.dev` はデフォルトでインターネット公開され、認証がないと task を第三者に閲覧・変更される。
- Cloudflare Access は公開アクセス自体は防げるが、Zero Trust 設定が煩雑だった。

### 制約事項

- 共有パスワード方式は単一ユーザー前提で、ユーザーごとの識別やデータ分割は提供しない。
- `AUTH_PASSWORD` / `SESSION_SECRET` はリポジトリに commit せず、Wrangler Secrets に保存する。
- パスワードリセットやユーザー登録は実装しない。

## 参考リンク

- [ADR 0019: Keep internal HTTP API private](0019-keep-internal-http-api-private.md)
- [ADR 0025: Define HTML and JSON error handling behavior](0025-define-html-and-json-error-handling-behavior.md)
- [Hono: Cookie Helper](https://hono.dev/docs/helpers/cookie)
- [Web Crypto: HMAC](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/sign)
