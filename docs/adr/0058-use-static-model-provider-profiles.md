# ADR 0058: モデルとproviderを静的profileで管理する

## 決定

- モデルとproviderの選択は静的なCLI profileで管理し、loopの工程ごとにprofileを選択する。
- profileのcatalogは実行中に生成・書換えせず、必要なsecretは環境変数から渡す。

### 決定の理由

- モデル選択の変更範囲をprofile単位に限定するため。
- 認証情報を設定ファイルや実行記録へ保存しないため。

## 不採用

- 実行ごとにcatalogを生成する方式
  - 実行結果が環境状態に依存し、再現性が下がるため。
- API keyをprofileやartifactへ保存する方式
  - 秘密情報の漏えい範囲が広がるため。

## 補足情報

### 背景

- ADR 0015から、共有homeと独立したモデル・provider選択の判断を記録する。

### 制約事項

- profileの実体とsecretの管理は実行環境の設定に従う。
- LLM clientの変更はADR 0037との整合性を確認する。

### 判断ごとの根拠と検証

| 検証ID | 判断・主張 | 根拠の種類 | 観測データ | データ充足条件 | 完了条件 | 許容できない結果 | 状態 | 再評価条件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | モデル選択を静的profileと環境変数で再現する | 既存方針 | profile、catalog、実行環境 | 各profileと必要なsecretの参照関係が確認できる | 実行時生成やsecretのartifact保存がない | profileが暗黙に変わる、またはsecretが記録される | 確認済み | providerやモデル管理方式の変更時 |
| - | loop工程ごとのprofile選択を固定する | 既存方針 | 各工程のprofile選択 | 工程ごとの選択が確認できる | 定めたprofileが選ばれる | 工程ごとの選択が暗黙に変わる | 確認済み | loop工程またはprofileの変更時 |

### 限界と再検討条件

- 限界: providerの利用可能性やモデル性能そのものは保証しない。
- 再検討条件: providerの追加、profileの動的選択、またはsecret管理方式の変更が必要になった場合。

## 参考リンク

- [ADR 0015](0015-worktree-scoped-codex-home.md)
- [ADR 0037](0037-switch-llm-client-to-opencode.md)
