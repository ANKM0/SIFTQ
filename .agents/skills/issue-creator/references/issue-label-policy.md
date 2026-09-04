# SIFTQ Issue Label Policy

## Default rule

新規 issue は、明示依頼がない限り taqt 対象外。

taqt 対象にする条件は次のどちらかです。

- ユーザーが issue 作成時に taqt 対象化を依頼した。
- 既存 issue に taqt 起動 label が付与された。

## Explicit taqt activation labels

`--taqt` は明示依頼時だけ。script が付ける。

- `taqt:enabled`
  - taqt の実行を明示的に許可する固定 label。状態や phase を表しません。

## Forbidden as manual assignment

- `taqt:pending`
- `taqt:phase:triage`
- `taqt:blocked`
- `taqt:running`
- `taqt:done`

これらは使用しない。script は受け取るとエラー。

## Optional labels

- 既存のプロジェクトラベル（機能種別、優先度など）があれば、内容に応じて追加可能。
- taqt 対象化の依頼がない場合は、taqt label を付与しません。
