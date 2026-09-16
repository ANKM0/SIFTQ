# ADR 0044: Place logical-to-physical mapping in the generator

## 決定
<!-- 決定事項、採用した内容とその理由を記載 -->

- 論理型（`string` / `boolean` / `number` / `datetime`）から物理型（D1）へのマッピングを生成器のコードに置く。
- `domain-model.json` に物理型（`db`）を持たせない。論理型は `domains` の定義に持つ。
- 物理の正本は `migrations/*.sql` とし、論理からの DDL 生成はしない。
- `migrations` と論理 + mapping の一致を検証する（実 schema との比較）。導入は warning からとする。

### 決定の理由
<!-- 決定事項、採用した内容の理由を記載 -->

- 物理依存（ベンダー型）をモデルから外し、論理モデルを純粋に保てる。
- SQLite に `boolean` / `datetime` が無く、`boolean→INTEGER` / `datetime→TEXT` の変換が暗黙になりやすい。明示して検証対象にする。
- mapping は小さい（4 型・方言 1）ため、別ファイルにするとソースが増えるだけになる。

## 不採用
<!-- 採用しなかった内容とその理由を記載 -->

- `domain-model.json` に `db` を持たせる
  - 論理モデルに物理が混入し、層が濁るため。
- mapping を独立した config ファイルにする
  - 現規模では管理対象が増えるだけで利点が薄いため。
- 論理から差分 migration（DDL）を自動生成する
  - D1 / SQLite の差分生成は複雑で、現状の頻度に見合わないため。

## 補足情報

### 背景
<!-- 解決する問題の背景やチームの状況などの戦略。 -->

- ADR 0007 で D1 を正本、ADR 0027 で migration を Git 管理する方針が確定している。
- 論理モデルと物理スキーマを分離しつつ、乖離は検出したい。

### 制約事項
<!-- ライブラリや設計の変更におけるトレードオフやできない事とその理由。 -->

- 方言が増える、mapping が育つ、非エンジニアが編集する、のいずれかで config へ切り出す。
- 本番（remote）への migration 適用はリリース作業として分離する（ADR 0034）。

## 参考リンク
<!-- ADRに関連する情報や参考にした資料へのリンク。 -->

- [ADR 0007: Cloudflare D1 を唯一の正本 DB として採用する](0007-adopt-cloudflare-d1-as-system-of-record.md)
- [ADR 0027: Adopt D1 SQL migration management](0027-adopt-d1-sql-migration-management.md)
- [ADR 0034: リリースと Worker デプロイを分離する](0034-separate-release-and-worker-deployment.md)
- [ADR 0043: Adopt single-source domain model JSON with generated diagrams](0043-adopt-single-source-domain-model-json.md)
