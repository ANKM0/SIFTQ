# Cloudflare Workers / D1 のデプロイ

Release と Worker デプロイの判断は [ADR 0034](../adr/0034-separate-release-and-worker-deployment.md) に従う。Release-only の手順は [Release](release.md) を参照する。

正規の本番URLは <https://app.siftq-app.workers.dev/>（Worker名 `app`）。旧 `siftq` Worker は廃止済みで、デプロイ・スモークは `app` を対象にする。

## デプロイ対象の判断

- Worker 実行成果物、D1 migration、または本番 secrets・設定を変更する場合は Worker をデプロイする。
- taqt、開発環境、CI、文書のみの変更は GitHub Release の対象にできるが、Worker はデプロイしない。
- デプロイする Release は、対象 SHA に固定したタグの clean な専用 worktree から実行する。

## 設定ファイル

- `cloudflare.config.ts`（ルート）: Worker 名、バインディング、secrets 宣言。cf が要求する場所に置く。
- `wrangler.config.ts`（ルート）: cf が使う Wrangler bundler のビルド設定。
- `.config/wrangler.jsonc`: ローカル D1 migration 専用。本番デプロイは読み込まない。

## 前提

- Cloudflare アカウントがある。
- Node.js 22.18 以降（cf は Node で動く。Bun 実行では config を読み込めない）。
- `. ./.config/env.sh` を実行し、`task -t .config/Taskfile.yml setup` 済み。

## 認証

対話的なログインを使う場合は次を実行する。

```bash
bun x cf auth login
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

`bun x cf d1 create siftq`

`cloudflare.config.ts` の `DB` binding は実際の D1 ID `20ca1496-cadc-4b40-9265-1d59d55d5b82` を指す。

## マイグレーションを適用する

リモート（本番）は database ID を指定する。

```bash
bun x cf d1 migrations apply 20ca1496-cadc-4b40-9265-1d59d55d5b82 --dir migrations
```

ローカルは `--local` を使うが、現行の cf beta は `cf d1 migrations apply --local` が終了しないため Wrangler で適用する。`cf dev` はローカル state に `.wrangler/state` を使い `--persist-to` を受け付けないため、同じ場所へ適用する。

```bash
bun x wrangler d1 migrations apply siftq --local -c .config/wrangler.jsonc --persist-to .wrangler/state
```

## Worker 認証の secrets を設定する

共有パスワード認証に必要な secrets をファイルへ書き出す。

```bash
task -t .config/Taskfile.yml deploy:secrets
```

対話入力を避ける場合は環境変数で渡す。

```bash
AUTH_PASSWORD="<password>" SESSION_SECRET="<long-random-secret>" task -t .config/Taskfile.yml deploy:secrets
```

`SESSION_SECRET` は長いランダム文字列を設定する。
`openssl rand -hex 32` で生成できる。
secrets は `tmp/cloudflare-secrets.env`（git 管理外）に保存され、デプロイ時に `cf deploy --secrets-file` で version へ注入される。
ローカル開発では `.dev.vars` に `AUTH_PASSWORD` / `SESSION_SECRET` を記載し、`.gitignore` 済みであることを確認する。

## Worker をデプロイする

```bash
task -t .config/Taskfile.yml deploy
```

コマンド末尾に表示される production URL で UI を確認する。

## 動作確認

正規URL <https://app.siftq-app.workers.dev/> を対象に確認する。

- 未認証では `/login` が表示され、ログイン後に Matrix UI が表示される。
- task の作成・更新・DnD 並べ替えが保存される。
- `bun x cf d1 migrations list 20ca1496-cadc-4b40-9265-1d59d55d5b82 --dir migrations` で適用済み migration を確認できる。
- Release Notes に対象 SHA、Worker デプロイ有無、migration 確認、本番確認結果を記録する。
