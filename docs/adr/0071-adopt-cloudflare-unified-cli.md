# ADR 0071: Cloudflare 操作 CLI に統合 CLI を採用する

## 決定

- Cloudflare の操作 CLI は Cloudflare 統合 CLI を主とする。
- ローカル開発、ビルド、型生成、本番デプロイを統合 CLI 経由で行う。
- 本番 secrets はデプロイ時にファイルから注入する。
- ローカル D1 migration は、統合 CLI のローカル実行が安定するまで Wrangler を併用する。

### 決定の理由

- 設定と Worker の型を単一の型付き定義から同期でき、設定とコードの乖離を防げる。
- Workers 以外の Cloudflare リソースも同一のコマンド体系で扱える。
- ローカル開発と本番デプロイの入口を一つの CLI に揃えられる。

## 不採用

- Wrangler を主 CLI として継続する。
  - 設定の型同期とリソース操作が複数ツールに分散するため。
- ローカル D1 migration も統合 CLI に置き換える。
  - 現行 beta はローカル D1 操作が処理後に終了せず、CI を停止させられないため。

## 補足情報

### 背景

- Wrangler は Workers と D1 に特化し、それ以外の Cloudflare リソース操作は別手段に分かれていた。
- 統合 CLI は Workers の設定を TypeScript で表現し、型推定とデプロイ時検証を提供する。

### 制約事項

- 統合 CLI は Node 実行を必要とし、Bun 実行では設定を読み込めない。
- secrets の単体更新は統合 CLI が未対応のため、デプロイ時のファイル注入に寄せる。
- ローカル D1 migration の一部機能は beta で未安定のため Wrangler を残す。

### 判断ごとの根拠と検証

| 検証ID | 判断・主張 | 根拠の種類 | 観測データ | データ充足条件 | 完了条件 | 許容できない結果 | 状態 | 再評価条件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V-071-001 | 統合 CLI のローカル D1 実行は安定して終了する | 観測 | ローカル D1 migration 適用の終了状態 | 適用成功と終了コードの組が複数回取得できる | 成功時に終了コードが正常で返る | 成功後も処理が終了しない | 否定 | 統合 CLI の beta 更新時 |
| V-071-002 | 統合 CLI の採用で Cloudflare 操作の入口が一つに揃う | 既存方針 | 開発・デプロイ・リソース操作の実行コマンド | 各操作が統合 CLI で実行できる | 主要操作が統合 CLI で完結する | 主要操作が別ツールを要求する | 暫定 | 主要操作の追加・変更時 |

### 限界と再検討条件

- 限界: 統合 CLI の全コマンド網羅と安定性は beta のため未確認。
- 再検討条件: 統合 CLI のローカル D1 実行が安定した時、または主要操作が統合 CLI で完結しなくなった時。

## 参考リンク

- [ADR 0027](0027-adopt-d1-sql-migration-management.md)
- [Cloudflare CLI](https://developers.cloudflare.com/cf/)
- [Wrangler からの移行](https://developers.cloudflare.com/cf/wrangler/)
