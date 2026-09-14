# ADR 0042: タスク編集draftをブラウザlocalStorageに保存する

## 決定

- New task と Task detail の未保存 title / description は、ブラウザの `localStorage` に一時draftとして保存する。
- draftは新規taskで1件、既存taskでtask IDごとに管理し、最終編集から24時間保持する。
- 同じtaskを複数タブで編集する場合は、task IDごとの同一キーへ保存し、最後に `localStorage` へ保存されたdraftを復元する。draftのマージやタブ間通信は行わない。
- Create / Save またはtask削除の成功後、対象draftを削除する。ログアウト時は現在のブラウザプロファイル内のdraftを削除する。
- D1はtaskの唯一の正本として維持し、draftをtaskデータの複製として扱わない。

### 決定の理由

- ブラウザ再起動後の復元を満たしつつ、既存のHTML駆動UIへ少ない変更で追加できる。
- title / description程度の小さいデータでは、入力停止後に保存することで性能上の負担を抑えられる。
- 同一オリジンの `localStorage` はタブ間で共有され、同じキーの `setItem` は既存値を置き換えるため、追加の同期機構なしで最後の保存を採用できる。
- D1にdraftを保存する方式と異なり、draft用のschema、認可、TTL削除、通信失敗処理を追加する必要がない。

## 不採用

- `sessionStorage`
  - タブやブラウザを閉じると内容が失われ、ブラウザ再起動後の復元を満たさないため。
- IndexedDB
  - title / descriptionの保存にはデータ量とAPIが過剰なため。
- D1へのdraft保存またはtaskデータの複製
  - 正本が二重化し、draft用のschema・認可・削除処理・競合処理が必要になるため。

## 補足情報

### 背景

- 編集中のtitle / descriptionが誤操作や画面遷移で失われるため、ローカルで復元可能なdraftを提供する。

### 制約事項

- `localStorage` は同一オリジンのJavaScriptから読み取れるため、パスワードやAPIキーなどの機密情報は対象にしない。
- `localStorage` には標準のTTLがないため、24時間経過時の削除は次回アプリ表示時に行う。
- localStorageが利用できない場合はdraft機能だけを失い、通常の入力・Create・Saveは継続する。
- サーバー側のversionがdraftの基準versionと異なる場合は、D1の正本を優先してdraftを破棄する。

## 参考リンク

- [Issue #399: 編集中のtask内容をローカルdraftとして保持する](https://github.com/ANKM0/SIFTQ/issues/399)
- [ADR 0007: Cloudflare D1を唯一の正本DBとして採用する](0007-adopt-cloudflare-d1-as-system-of-record.md)
