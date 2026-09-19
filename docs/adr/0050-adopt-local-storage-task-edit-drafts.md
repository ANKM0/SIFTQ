# ADR 0050: タスク編集draftをブラウザlocalStorageに保存する

## 決定

- 既存 task を編集するときの未保存 title / description は、ブラウザの `localStorage` に一時draftとして保存する。
- New task の title / description は draft として保存も復元もしない。
- task データの唯一の正本は D1 のままとし、draft を task データの複製として扱わない。

### 決定の理由

- New task では、入力途中で cancel（やっぱやめた）してから作成し直す方が、追加時に削除した入力を復元するより多い。前回入力が残ると新規作成のたびに消す手間が発生する。
- 既存 task の編集では、誤操作や画面遷移で編集中の内容が失われると再入力の負担が大きいため、draft を維持する。

## 不採用

- New task の入力を draft として保存・復元する。
  - cancel 後の再作成を繰り返す利用場面で前回入力の削除が必要になり、入力の削除より復元の需要が小さいため。
- サーバー側（D1）への draft 保存。
  - 正本が二重化し、draft 用の schema・認可・削除処理・競合処理が必要になるため。

## 補足情報

### 背景

- ADR 0042 は New task と Task detail の双方を draft 保存の対象としていた。#471 で New task を対象外に変更したため、ADR 0042 を置き換える。

### 制約事項

- パスワードや API キーなどの機密情報は draft の対象にしない。
- draft が利用できない場合でも、通常の入力・Create・Save は継続する。

## 参考リンク

- [Issue #471: 新規タスク作成時に下書きを保存しない](https://github.com/ANKM0/SIFTQ/issues/471)
- [Issue #399: 編集中のtask内容をローカルdraftとして保持する](https://github.com/ANKM0/SIFTQ/issues/399)
- [ADR 0042: タスク編集draftをブラウザlocalStorageに保存する](0042-adopt-local-storage-task-edit-drafts.md)
- [ADR 0007: Cloudflare D1を唯一の正本DBとして採用する](0007-adopt-cloudflare-d1-as-system-of-record.md)
