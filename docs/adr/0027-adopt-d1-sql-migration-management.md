# ADR 0027: Adopt D1 SQL migration management

## 決定

- D1 の schema 変更は Cloudflare 公式の SQL migration + Wrangler で管理する。
- migration は Git 管理する。
- 適用済み migration は書き換えず、変更は新しい migration を追加する。
- ローカルは `--local`、本番は `--remote` で適用する。

### 決定の理由

- 追加ツールや ORM を使わず、Cloudflare 公式手順で再現できる。
- 適用履歴が D1 側に残り、ローカルと本番で同じ手順を使える。

## 不採用

- 独自 migration スクリプト
  - 履歴管理と再現性を自前で持つ必要があるため。

## 補足情報

### 背景

- ADR 0026 の task data model を D1 へ反映する運用を決める。

### 制約事項

- migration は repository 層に閉じ、D1 binding 経由で適用する。

## 参考リンク

- [Cloudflare D1: Migrations](https://developers.cloudflare.com/d1/reference/migrations/)
