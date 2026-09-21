# ADR 0062: HTMXのエラー表示とstatus変換を共通化する

## 決定

- 内部エラーの意味からHTTP statusへの変換は共通化する。
- HTML UIのエラー表示はHTML fragmentと共通のHTMX response headerで扱う。

### 決定の理由

- エラーstatusの意味とHTMXの表示経路を共通化するため。
- HTMXの画面更新経路を各endpointで重複実装しないため。

## 不採用

- endpointごとにHTMXエラー表示を実装する方式
  - 表示先と置換方法が不統一になるため。

## 補足情報

### 背景

- ADR 0025から、HTMX表示とstatus変換を内部エラー開示や認証挙動から分離して記録する。

### 制約事項

- JSON error bodyはADR 0023、HTTP statusの分類はADR 0024に従う。

### 判断ごとの根拠と検証

| 検証ID | 判断・主張 | 根拠の種類 | 観測データ | データ充足条件 | 完了条件 | 許容できない結果 | 状態 | 再評価条件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | HTMXのエラー表示経路を共通化する | 既存方針 | エラーresponse headerと画面更新 | 代表的なHTMXエラー表示が確認できる | 表示先と置換方法が共通になる | endpointごとに表示経路が異なる | 確認済み | HTMXのエラー表示方式の変更時 |
| - | 内部エラーからHTTP statusへの変換を共通化する | 既存方針 | error typeとHTTP statusの対応 | 代表的な内部エラーの対応が確認できる | 同じ意味のエラーが同じstatusへ変換される | endpointごとにstatusの意味が変わる | 確認済み | エラー分類の変更時 |

### 限界と再検討条件

- 限界: ネイティブアプリなどHTML・JSON以外のclientは対象外とする。
- 再検討条件: 新しいclientの応答形式が必要になった場合。

## 参考リンク

- [ADR 0025](0025-define-html-and-json-error-handling-behavior.md)
- [ADR 0023](0023-adopt-rfc9457-error-body.md)
- [ADR 0024](0024-map-errors-to-standard-http-status-codes.md)
