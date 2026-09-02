# ADR 0036: Adopt Better Auth as future authentication migration target

## 決定

- 将来のユーザー別認証・認可の移行先として Better Auth を採用する。
- 当面は ADR 0032 の共有パスワード認証を維持する。本 ADR は ADR 0032 を置き換えず、実装移行までの方針を定める。
- 実装移行時は `tasks.owner_id` を Better Auth の user ID に接続する。
- Cloudflare Workers / Hono / D1 を前提とし、実装移行時に Better Auth の user / session / account / verification に相当する D1 schema を追加する。

### 決定の理由

- Better Auth は Cloudflare Workers / Hono / D1 での構成を前提にでき、共有パスワード認証からユーザー別認証・認可へ段階的に移行できる。
- 認証方式や既存データ移行が未確定の段階で ADR 0032 を置き換えると実装コストが先行するため、まず移行先と接続方針だけを固定する。
- `tasks.owner_id` を Better Auth の user ID に接続すると決めることで、ADR 0026 の所有者分離方針を将来の認証基盤へ接続できる。

## 不採用

- Worker 内に本格的なユーザー別認証を自前実装する
  - パスワードハッシュ、セッション、OAuth、アカウント連携を自前で維持する必要があり、認証基盤としての実装・運用コストが高いため。
- 本 ADR で具体的な認証方式と既存 `owner_id` の移行方法まで決定する
  - 認証方式と既存データの帰属先は実装開始時に確定すべき内容で、ADR の責務を超えるため。

## 補足情報

### 背景

- 現行の認証は ADR 0032 の共有パスワード認証で、単一ユーザー利用を前提とする。
- ADR 0026 は task に `owner_id` を持たせ、取得・更新の条件へ常に含める方針を定めている。
- 将来のユーザー別認証・認可では `tasks.owner_id` を実ユーザーへ接続する必要があるが、移行先の認証基盤が未決定だった。

### 制約事項

- Better Auth の依存追加、Cloudflare Workers 互換フラグ、D1 migration、認証画面の実装は本 ADR の範囲外とする。
- email / password、OAuth provider、ユーザー登録可否などの具体的な認証方式は後続の feature / Issue で決定する。
- 既存 `owner_id = "local"` データの移行手順は実装開始時の Issue で決定する。

## 参考リンク

- [ADR 0032: Adopt Worker-managed shared-password authentication](0032-adopt-worker-managed-shared-password-authentication.md)
- [ADR 0026: Define task data model](0026-define-task-data-model.md)
- [Better Auth](https://www.better-auth.com/)
- [Cloudflare Workers](https://developers.cloudflare.com/workers/)
- [Hono](https://hono.dev/)
