# ADR 0043: Adopt single-source domain model JSON with generated diagrams

## 決定
<!-- 決定事項、採用した内容とその理由を記載 -->

- ドメイン / データモデルの構造の正本を `docs/requirements/assets/domain-model/domain-model.json` の 1 ファイルにする。
- `docs/requirements/assets/domain-model/domain-model.schema.json` を先に更新し、生成器の入口で検証する。
- 図は D2 を描画先として生成する（`logical` / `physical` / `flow` / `nav`）。生成物は追跡せず task で再生成する。
- ドメイン図（集約 / 値オブジェクト / 不変条件）は手書きの `domain-model.d2` とし、`concept.d2`（概念データ図）は作らない。
- 図 → JSON の逆生成はしない。

### 決定の理由
<!-- 決定事項、採用した内容の理由を記載 -->

- 同じ構造が `domain.md`、`migrations`、各図に分散し、手で同期する前提だと乖離と手戻りが起きる。
- 実装前にデータの形を 1 箇所で確定でき、画面 / API / 型の手戻りを減らせる。
- JSON を機械が読む前提にすると、コメントや暗黙の型変換を持たず検証しやすい。

## 不採用
<!-- 採用しなかった内容とその理由を記載 -->

- D2 を正本にする
  - D2 は表現力が高く逆変換が脆い。不変条件のような本文を運べないため。
- `concept.d2` を生成物として残す
  - 同じ `entities` に `domain` 型を付けただけで ER の言い換えになり、ドメイン図として機能しないため。
- 図 → JSON の双方向同期
  - 逆変換の実装と保守が過剰で、正本が曖昧になるため。

## 補足情報

### 背景
<!-- 解決する問題の背景やチームの状況などの戦略。 -->

- ADR 0007 で D1 を正本、ADR 0026 でデータモデルを定義済み。図は用途別に Mermaid / D2 / drawio へ分散していた。
- 複数ツールと画像により図と実装が同期されず、実装前に構造を合意しづらかった。

### 制約事項
<!-- ライブラリや設計の変更におけるトレードオフやできない事とその理由。 -->

- 生成物（`*.d2` / `*.svg`）は追跡しない。再生成は task で行う。
- フル UI の生成と `mapping.md` は対象外。UI は画面遷移図までとする。

## 参考リンク
<!-- ADRに関連する情報や参考にした資料へのリンク。 -->

- [ADR 0007: Cloudflare D1 を唯一の正本 DB として採用する](0007-adopt-cloudflare-d1-as-system-of-record.md)
- [ADR 0026: Define task data model](0026-define-task-data-model.md)
- [ADR 0044: Place logical-to-physical mapping in the generator](0044-place-logical-to-physical-mapping-in-generator.md)
