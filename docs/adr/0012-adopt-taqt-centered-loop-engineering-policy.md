# ADR 0012: taqt 中心の loop engineering 実行方針

## 決定

- GitHub Issue を要求、CUJ、AC/DoD、議論の正本とする。taqt task は Issue を source として作成し、status、phase、worker、run などの実行状態を管理する。
- loop runner は宣言された loop の step 遷移、agent 実行、観測、再試行、停止を管理する。GitHub 監視、同期、branch、commit、PR などの外部連携は script adapter として分離する。
- 各 run の `state.json`、`events.jsonl`、artifact を実行記録とする。design step の判断と検証結果は `artifacts/design-decision.md` に保存し、イベントと report から追跡できるようにする。
- 実行は設計、テスト、実装、観測、判断、独立検証の流れで進め、仕様矛盾、プロダクト判断、権限外変更、繰り返し失敗は人間へエスカレーションする。

### 決定の理由

- 要求の正本と実行状態を分離すると、Issue の意図を保ったまま taqt の再試行・停止・worker 管理を再現できるため。
- run 単位の状態、イベント、artifact に判断と検証を集約すると、実装時の設計判断を時系列で追跡できるため。
- 外部連携を adapter に分離すると、loop runner の実行ロジックを保ったまま連携先を変更できるため。

## 不採用

- GitHub Issue だけで実行状態を管理する。
  - worker、phase、run state、観測結果を Issue 上で管理すると、再試行と自動処理の状態を追跡しにくいため。
- loop runner が GitHub 監視や同期を直接担当する。
  - 外部連携の変更が loop 実行ロジックへ波及し、runner の責務が広がるため。
- PR ごとの設計文書を実行時の設計判断の正本として残す。
  - run と判断・検証結果の対応が分断され、再試行を含む時系列を追跡しにくいため。

## 補足情報

### 背景

- この方針は、Issue #134 に記録されていた taqt-centered loop engineering の恒久的な判断を ADR に移管したものである。
- Issue #166 で run artifact への設計判断の保存と参照を追加し、PR 単位の設計文書運用を廃止する。

### 制約事項

- GitHub Issue の要求、AC/DoD、議論を taqt artifact に移管しない。
- run artifact は各 run の判断・検証記録とし、run 横断の集計や自動改善は別の判断とする。
- 通常のプロダクト開発における ADR の運用は変更しない。

## 参考リンク

- [PR #134](https://github.com/ANKM0/SIFTQ/pull/134)
- [Issue #166](https://github.com/ANKM0/SIFTQ/issues/166)
- [ADR 0002](0002-separate-adr-and-design-docs.md)
