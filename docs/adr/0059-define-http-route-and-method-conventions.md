# ADR 0059: HTTP routeとmethodの規約を定める

## 決定

- 内部APIのrouteは名詞・複数形・kebab-case・末尾slashなしを基本とし、CRUD動詞を含めず、検索・絞り込みはquery parameterで表現する。
- カスタム操作だけは例外的に動詞を許容する。HTML UIはGET・POST、内部APIはGET・POST・PATCH・DELETEを基本とする。

### 決定の理由

- routeとmethodをリソース指向に揃え、API契約を一貫させるため。
- HTML formと内部APIの責務を分けるため。

## 不採用

- CRUD動詞をrouteへ含める方式
  - routeが操作中心になり、リソース指向と一貫しないため。
- すべての操作を同じmethodで表す方式
  -標準HTTP semanticsを失うため。

## 補足情報

### 背景

- ADR 0021から、route・methodの規約を応答形式やversion方針から分離して記録する。

### 制約事項

- resource-oriented RESTの判断はADR 0020に従う。
- 個別resourceの操作は各機能のADRで定める。

### 判断ごとの根拠と検証

| 検証ID | 判断・主張 | 根拠の種類 | 観測データ | データ充足条件 | 完了条件 | 許容できない結果 | 状態 | 再評価条件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | routeとmethodをリソース指向で統一する | 既存方針 | API route、method、queryの定義 | 対象routeの命名とmethodが確認できる | CRUD動詞を含まず、操作が標準methodで表現される | routeが操作名中心になる | 確認済み | API設計方針の変更時 |
| - | query parameterとカスタム操作の例外を一貫して扱う | 既存方針 | 検索・絞り込み・カスタム操作 | 代表的なqueryと操作routeが確認できる | queryはparameter、例外だけ動詞で表現される | queryや通常CRUDに動詞routeを使う | 確認済み | API設計方針の変更時 |

### 限界と再検討条件

- 限界: 外部公開APIの互換性方針は対象外とする。
- 再検討条件: APIを外部公開し、互換性維持が必要になった場合。

## 参考リンク

- [ADR 0021](0021-define-http-api-contract-conventions.md)
- [ADR 0020](0020-adopt-resource-oriented-rest-for-internal-api.md)
