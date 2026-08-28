# ADR 0031: Adopt Cloudflare Access for SIFTQ Worker access control

## 決定

- `siftq` Worker へのアクセスを Cloudflare Access で保護し、Cloudflare アカウントのメンバーに限定する。
- 将来、ユーザーごとの配布・データ分割が必要になった場合は、Worker 内認証（セッション / API キー）の採用を再検討する。

### 決定の理由

- コード変更なしで、`/` と `/api` のすべてのエンドポイントを一括で保護できる。
- 現状の利用者は個人（Cloudflare アカウント所有者）のみで、アカウントメンバー限定で十分。
- Cloudflare Access は `workers.dev` を含む Worker の全ホスト名を保護できるため、デプロイ URL を変更する必要がない。

## 不採用

- Worker 内認証（セッション / API キー）
  - 個人利用の現段階では、実装・保守・認証 UI のコストが保護要件を上回るため。
  - ユーザーごとのデータ分割や外部プログラムからの API 利用が必要になった時点で再検討する。

## 補足情報

### 背景

- `*.workers.dev` はデフォルトでインターネット公開され、URL を知る第三者がアクセスできる。
- 現在の `siftq` Worker には認証がなく、task の閲覧・作成・変更が第三者に可能な状態。
- ADR 0019 では API を内部 IF と位置づけているが、アクセス制御は未実装だった。

### 制約事項

- Cloudflare Access は認証境界であり、ユーザーごとのデータ分割は提供しない。
- タスクデータは引き続き全員で共有され、将来のユーザー別分割には Worker 内認証と owner による分離が必要。
- Zero Trust の有効化と Access 設定は Cloudflare ダッシュボード上で実施する。

## 参考リンク

- [ADR 0019: Keep internal HTTP API private](0019-keep-internal-http-api-private.md)
- [Cloudflare Access · Cloudflare Workers docs](https://developers.cloudflare.com/workers/configuration/cloudflare-access/)
