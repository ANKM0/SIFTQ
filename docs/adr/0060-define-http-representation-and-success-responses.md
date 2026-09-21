# ADR 0060: HTTPの表現形式と成功レスポンスを定める

## 決定

- HTML UIの応答はtext/html、内部APIの要求・応答はapplication/jsonを基本とする。
- 成功レスポンスは、取得200、作成201とLocationおよび作成後resource、更新200、削除204、reorder 200を基本とする。

### 決定の理由

- UIとAPIの利用者が期待する表現形式を混在させないため。
- HTTP semanticsに沿った応答を共通化するため。

## 不採用

- HTML UIとJSON APIで同じ表現形式を返す方式
  - 利用側の責務とエラー処理が混ざるため。
- 成功時もすべて同じstatusを返す方式
  - 作成・更新・削除の結果を区別できないため。

## 補足情報

### 背景

- ADR 0021から、表現形式と成功応答の判断をroute・method方針から分離して記録する。

### 制約事項

- エラー応答の形式はADR 0023と0062に従う。
- 個別endpointの詳細契約はAPI実装とテストで管理する。

### 判断ごとの根拠と検証

| 検証ID | 判断・主張 | 根拠の種類 | 観測データ | データ充足条件 | 完了条件 | 許容できない結果 | 状態 | 再評価条件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | UIとAPIの表現形式・成功応答を分離する | 既存方針 | response media type、status、body | 対象endpointの成功応答が確認できる | UIはHTML、APIはJSONで、操作に対応するstatusになる | 表現形式やstatusがendpointごとに不統一になる | 確認済み | API契約の変更時 |
| - | 作成・更新・削除の成功応答を区別する | 既存方針 | 各methodのstatusとbody | 代表的な作成・更新・削除応答が確認できる | 作成時のLocationとresourceを含め、methodに対応するstatusになる | 成功結果がstatusとbodyから判別できない | 確認済み | API契約の変更時 |
| - | reorderの成功応答を定める | 既存方針 | reorderのstatusとbody | reorder操作の応答が確認できる | 成功時に200を返す | reorderの成功結果が他の操作と混同される | 確認済み | reorder契約の変更時 |

### 限界と再検討条件

- 限界: 外部clientとの互換性やAPI versioningは定めない。
- 再検討条件: 外部clientを追加する場合。

## 参考リンク

- [ADR 0021](0021-define-http-api-contract-conventions.md)
- [ADR 0023](0023-adopt-rfc9457-error-body.md)
