# SIFTQ Issue Label Policy

## Default rule

新規 issue は、明示依頼がない限り taqt 対象外。

taqt 対象にする条件は次のどちらかです。

- ユーザーが issue 作成時に taqt 対象化を依頼した。
- 既存 issue に taqt 起動 label が付与された。

## Explicit taqt activation labels

`--taqt` は明示依頼時だけ。script が付ける。

- `taqt:pending`
  - taqt が pick up する起動状態。明示された taqt 対象 issue にのみ付与します。
- `taqt:phase:triage`
  - taqt 対象 issue の初期実行フェーズ。

## Forbidden as manual assignment

- `taqt:blocked`
- `taqt:running`
- `taqt:done`

taqt が更新する。script は受け取るとエラー。

## Optional labels

- 既存のプロジェクトラベル（機能種別、優先度など）があれば、内容に応じて追加可能。
- taqt 対象化の依頼がない場合は、taqt label を付与しません。
