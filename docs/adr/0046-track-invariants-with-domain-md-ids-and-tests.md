# ADR 0045: Track invariants with domain.md IDs and test names

## 決定
<!-- 決定事項、採用した内容とその理由を記載 -->

- 不変条件の本文は `docs/requirements/domain.md` に置き、`INV-TM-xxx` の ID を振る。
- `domain-model.json` は `rules` で ID のみを参照し、本文を持たない。
- テスト名に `INV-TM-xxx` を含める。
- 生成器の `check()` が dangling（JSON にあって `domain.md` に無い）、orphan（`domain.md` にあって未参照）、テスト欠落を検出する。

### 決定の理由
<!-- 決定事項、採用された内容の理由を記載 -->

- 実行できないルールの本文を JSON に書くと、静かに腐る。
- ID を 1 箇所（`domain.md`）に置き、参照とテストを突き合わせるだけで、網羅と乖離を機械検証できる。

## 不採用
<!-- 採用しなかった内容とその理由を記載 -->

- JSON に不変条件の本文を書く
  - 実行されず、コードや文書と乖離するため。
- 独自 DSL / ルールエンジンで不変条件を評価する
  - 言語と評価器の設計・保守が過剰で、既存の純粋関数とテストで足りるため。
- 対応表を別ファイルで持つ
  - 対応表自体が古くなるため。

## 補足情報

### 背景
<!-- 解決する問題の背景やチームの状況などの戦略。 -->

- ADR 0006 / 0029 で、ドメインは構造体型・純粋関数・`Result` とし、不変条件の強制はコードとテストが担う方針。
- `domain-model.json` を構造の正本にしたとき、不変条件との紐づけが失われがちになる。

### 制約事項
<!-- ライブラリや設計の変更におけるトレードオフやできない事とその理由。 -->

- ID を振る対象は、ドメインとして守るべき不変条件に限る。すべての記述を ID 化しない。

## 参考リンク
<!-- ADRに関連する情報や参考にした資料へのリンク。 -->

- [ADR 0006: アーキテクチャとして、軽量アプリケーションアーキテクチャを採用する](0006-adopt-lightweight-application-architecture.md)
- [ADR 0029: Adopt Result type in domain and usecase](0029-adopt-result-type-in-domain-usecase.md)
- [ADR 0043: Adopt single-source domain model JSON with generated diagrams](0043-adopt-single-source-domain-model-json.md)
