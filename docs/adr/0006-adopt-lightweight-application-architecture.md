# ADR 0006: アーキテクチャとして、軽量アプリケーションアーキテクチャを採用する

## 決定
<!-- 決定事項、採用した内容とその理由を記載 -->

- クリーンアーキテクチャを崩したshアーキテクチャを採用する。
- 詳細は [docs/contributing/architecture.md](../contributing/architecture.md) を参照

### 決定の理由
<!-- 決定事項、採用した内容の理由を記載 -->

- mvpの段階ではクリーンアーキテクチャは冗長で重過ぎるが、Active Recordなどを採用すると、爆速だが将来拡張しにくい構成になる。
- 拡張可能性と実装速度のちょうどよいバランスを考えた結果、クリーンアーキテクチャを少し崩した形を採用した。


## 不採用
<!-- 採用しなかった内容とその理由を記載 -->

- MVC
  - mvp段階では、よい選択肢だが、昔やった経験として将来的に読みづらいコードになりがちなため却下。
- Clean Architecture を厳密に導入する。
  - 小規模開発だと冗長すぎるため却下。

## 補足情報

### 背景
<!-- 解決する問題の背景やチームの状況などの戦略。 -->

- mvpから初めて拡張していきたい
  - → ドメインロジックと入出力は分離しつつ、小規模な新規開発では最初から interface を増やさないのがいいのでは?

### 制約事項
<!-- ライブラリや設計の変更におけるトレードオフやできない事とその理由。 -->

- CUI は実装しない。task データの正本は ADR 0007 に従い Cloudflare D1 とし、Worker を経由して操作する。
- 将来差し替えを見越した repository interface や storage adapter は先に作らない。
- 実装速度を落とす過剰な層分割は避ける。
- D1 を正本とする判断は ADR 0007 の責務である。

## 参考リンク
<!-- ADRに関連する情報や参考にした資料へのリンク。 -->

- [Task Management Domain](../requirements/domain.md)
- [Task Management 要求分析](../requirements/requirements-analysis.md)
- [小規模から成長させるアプリケーションアーキテクチャ](https://note.com/suwash/n/n869c06c749e6)
- [ADR 0005: 個人向け自動同期まで Cloudflare/TanStack 採用を延期する](0005-defer-cloudflare-tanstack-until-personal-sync.md)
- [ADR 0007: Cloudflare D1 を唯一の正本 DB として採用する](0007-adopt-cloudflare-d1-as-system-of-record.md)
