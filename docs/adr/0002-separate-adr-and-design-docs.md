# ADR 0002: ADRとDesign Docを分けて記録する

> Status: Superseded by [ADR 0012](0012-adopt-taqt-centered-loop-engineering-policy.md).

この ADR は過去の運用判断の記録として保持する。現在の要求は
`docs/requirements/`、恒久的な判断は `docs/adr/`、実行時の設計判断と検証結果は
taqt run artifact を正本とする。

## 目的
<!-- 解決したい課題はXXX。 -->

ADR と Design Doc の使い分けを定義し、設計検討と意思決定の履歴を追えるようにする。

## 背景
<!-- 解決する問題の背景やチームの状況などの戦略。 -->

機能単位の設計検討とリポジトリ全体に影響する意思決定を同じ場所に残すと、後から経緯を追いにくくなる。

参照記事では、ADR はアーキテクチャに関わる意思決定、Design Doc は機能や設計に焦点を当てた検討として分けて扱っている。
この考え方を SIFTQ の既存ドキュメント構成に合わせて導入する。

## 制約事項
<!-- ライブラリや設計の変更におけるトレードオフやできない事とその理由。 -->

- 既存の ADR 運用、repository script、skill の責務分離を維持する。
- requirements と UI プレビューの正は既存の `docs/requirements/` と `docs/wireframes/` に置く。
- Issue の AC / DoD は Issue 側に置き、Design Doc には重複させない。

## 内容

### 採用した内容
<!-- 採用した内容とその理由を記載 -->

- ADR と Design Doc を別の文書種別として扱う。ADR は横断的な意思決定、Design Doc は機能や設計検討を記録する。
  - ADR は横断的な意思決定、Design Doc は機能や設計検討を記録するため。
- 当時は Design Doc を PR ごとに 1 つ作成し、機能単位の設計検討を記録した。
  - 設計検討を実装単位と紐づけ、PR review から参照しやすくするため。
- Design Doc の検討中に横断的な意思決定が発生した場合は、別途 ADR を作成して相互参照する。
  - 機能固有の検討と長期的な意思決定を混ぜないため。

### 採用しなかった内容
<!-- 採用しなかった内容とその理由を記載 -->

- Design Doc を ADR に統合する。
  - ADR の粒度が大きくなり、機能単位の検討と横断的な意思決定が混ざるため却下。
- Design Doc を Issue description だけで管理する。
  - 実装完了後に設計検討だけを一覧、再利用、参照しにくいため却下。

## 影響範囲
<!-- ADRの決定が及ぼす可能性のある影響範囲。 -->

- `docs/requirements/`
- `docs/adr/`
- `.taqt/runs/*/artifacts/`
- 今後の feature-level design と architecture decision の記録方法

## 参考リンク
<!-- ADRに関連する情報や参考にした資料へのリンク。 -->

- [ADRとDesign Docで開発組織の生産性を向上するためのドキュメンテーション文化を醸成する](https://qiita.com/SoarTec-lab/items/c50a931e5cc1a4cb0b59)
