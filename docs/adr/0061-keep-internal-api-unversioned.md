# ADR 0061: 内部APIにversionを付けない

## 決定

- 内部APIはversion prefixを付けず、単一repository内でclientとserverを同時に追従させる。
- 外部公開や複数clientとの互換性が必要になった場合にversion方針を再検討する。

### 決定の理由

- 現在のAPI利用者と実装を同一repositoryで管理しているため。
- 外部clientとの互換性境界がまだ存在しないため。

## 不採用

- 初期から複数versionを維持する方式
  - 外部互換性がない段階では管理コストが先行するため。

## 補足情報

### 背景

- ADR 0021から、versioningの判断をroute・method・responseの規約から分離して記録する。

### 制約事項

- 外部公開APIの互換性要件が発生した場合は、この判断を再評価する。

### 判断ごとの根拠と検証

| 検証ID | 判断・主張 | 根拠の種類 | 観測データ | データ充足条件 | 完了条件 | 許容できない結果 | 状態 | 再評価条件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | 内部APIを単一versionで運用する | 既存方針 | API利用者とrepository構成 | API利用者が同一repositoryで追従することを確認できる | version分岐なしでclientとserverを更新できる | 複数clientの互換性が必要なのにversionがない | 確認済み | 外部clientの追加時 |

### 限界と再検討条件

- 限界: 外部clientや独立リリースを想定しない。
- 再検討条件: 外部公開、独立リリース、または複数versionの共存が必要になった場合。

## 参考リンク

- [ADR 0021](0021-define-http-api-contract-conventions.md)
