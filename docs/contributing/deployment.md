# Cloudflare Workers / D1 のデプロイ

Release と Worker デプロイの判断は [ADR 0034](../adr/0034-separate-release-and-worker-deployment.md) に従う。Release-only の手順は [Release](release.md) を参照する。

## デプロイ対象の判断

- Worker 実行成果物、D1 migration、または本番 secrets・設定を変更する場合は Worker をデプロイする。
- taqt、開発環境、CI、文書のみの変更は GitHub Release の対象にできるが、Worker はデプロイしない。
- デプロイする Release は、対象 SHA に固定したタグの clean な専用 worktree から実行する。

## 前提

- Cloudflare アカウントがある。
- `task setup` 済みで、`bun x wrangler` が実行できる。

## 認証

対話的なログインを使う場合は次を実行する。

```bash
bun x wrangler login
```

CI など対話できない環境では、Cloudflare の API Token を使う。

```bash
export CLOUDFLARE_API_TOKEN="<api-token>"
```

Token には次の権限が必要。

- Account / Workers Scripts / Edit
- Account / D1 / Edit

複数アカウントを扱う場合は `CLOUDFLARE_ACCOUNT_ID` も設定する。

## リモート D1 を作成する

`bun x wrangler d1 create siftq`

`wrangler.jsonc` は `database_name` で D1 を参照するため、作成した database 名が
`siftq` であれば設定変更は不要。

## マイグレーションを適用する

`bun x wrangler d1 migrations apply siftq --remote`

## Worker 認証の secrets を設定する

共有パスワード認証に必要な secrets を設定する。

```bash
task deploy:secrets
```

対話入力を避ける場合は環境変数で渡す。

```bash
AUTH_PASSWORD="<password>" SESSION_SECRET="<long-random-secret>" task deploy:secrets
```

`SESSION_SECRET` は長いランダム文字列を設定する。
`openssl rand -hex 32` で生成できる。
ローカル開発では `.dev.vars` に `AUTH_PASSWORD` / `SESSION_SECRET` を記載し、
`.gitignore` 済みであることを確認する。

## Worker をデプロイする

```bash
task deploy
```

コマンド末尾に表示される production URL で UI を確認する。

## 動作確認

- 未認証では `/login` が表示され、ログイン後に Matrix UI が表示される。
- task の作成・更新・DnD 並べ替えが保存される。
- `bun x wrangler d1 migrations list siftq --remote` で適用済み migration を確認できる。
- Release Notes に対象 SHA、Worker デプロイ有無、migration 確認、本番確認結果を記録する。
