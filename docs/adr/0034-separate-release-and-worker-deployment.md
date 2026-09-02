# ADR 0034: リリースと Worker デプロイを分離する

## 決定

- GitHub Release はリポジトリ変更の配布単位、Cloudflare Workers デプロイは本番 Worker を更新する操作として分離する。
- Worker 実行成果物、D1 migration、または本番 secrets・設定に影響する変更は Release とデプロイを行う。taqt、開発環境、CI、文書だけの変更は Release-only とし、Worker をデプロイしない。
- Release 候補は対象 SHA をタグへ固定し、clean な専用 worktree から検証・デプロイする。
- `0.x` では、バグ修正と本来の挙動の補完は patch、後方互換な利用者向け新機能は minor とする。

### 決定の理由

- リポジトリの変更履歴を Release として追跡しつつ、Worker を変更しない開発運用の変更で本番を不要に更新しないため。
- 本来提供されるべきだった機能の補完である #276 のような変更を patch と一貫して判断するため。
- タグ、実行した成果物、検証結果を対応付け、再現可能な本番変更にするため。

## 不採用

- すべての GitHub Release で Worker をデプロイする。
  - Worker に無関係な変更でも本番を更新し、必要な検証範囲が広がるため。
- Worker のデプロイだけを記録し、Release を作らない。
  - taqt・CI・文書の変更を含むリポジトリの配布履歴を追跡できないため。

## 補足情報

### 背景

- v0.5.1 では UI 修正と Matrix からの新規作成を Worker へデプロイし、v0.5.2 では taqt・文書のみを Release-only とした。判断と検証記録を継続可能な運用として明文化する。

### 制約事項

- Release とデプロイの対象・検証結果は Release Notes に記録する。D1 migration がある場合は remote 適用状況を確認してからデプロイする。
- 認証が必要な本番操作のスモークテストは、認証可能な担当者が実施・記録する。

## 参考リンク

- [Release 手順](../contributing/release.md)
- [Cloudflare Workers / D1 のデプロイ](../contributing/deployment.md)
- [Issue #280](https://github.com/ANKM0/SIFTQ/issues/280)
