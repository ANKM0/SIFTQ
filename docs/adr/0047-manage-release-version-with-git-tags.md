# ADR 0047: Manage release version with git tags

## 決定
<!-- 決定事項、採用した内容とその理由を記載 -->

- バージョンの正本は **git タグ**（`vX.Y.Z`）とする。
- `package.json` は `version` を持たない。
- リリースは release commit を作らず、clean な専用 worktree の SHA にタグを付けて行う。
- `release:version` タスクと、`package.json` の version を使う一致チェックを削除する。CI の version 監視（`scripts/ci/check_package_version.py` とそのテスト）も削除する。

### 決定の理由
<!-- 決定事項、採用した内容の理由を記載 -->

- `package.json` の `version` はリリースツールしか読まず、実行時・CI・Worker では未使用。
- release commit が main に入らず `package.json` が古いまま残る問題（main は 0.12.0、最新タグは v0.14.1）を、正本をタグに一本化して解消する。
- release commit が不要になり、リリースは「clean worktree の SHA にタグ」だけで完結する。

## 不採用
<!-- 採用しなかった内容とその理由を記載 -->

- `package.json` の `version` を維持し、リリースコミットを main にマージして同期する
  - main へのマージ手順が増え、タグとメタデータの二重管理が続くため。
- リリースコミットを main に直接コミットする
  - main の保護とレビュー方針に反するため。

## 補足情報

### 背景
<!-- 解決する問題の背景やチームの状況などの戦略。 -->

- ADR 0034 でリリースと Worker デプロイを分離し、`0.x` の patch / minor 基準を定めている。
- v0.12.1 以降のタグは main の祖先ではなく、main の `package.json` が更新されない状態が続いていた。

### 制約事項
<!-- ライブラリや設計の変更におけるトレードオフやできない事とその理由。 -->

- タグと `package.json` の相互チェックが無くなるため、タグ対象は `release:plan` の `--ref` と `--base` で確認する。
- 既存タグ（v0.12.1〜v0.14.1）は `package.json` に version を持つ。今後のタグは持たない。
- `private: true` のアプリで publish しないため、version 無しの実害は無い。

## 参考リンク
<!-- ADRに関連する情報や参考にした資料へのリンク。 -->

- [ADR 0034: リリースと Worker デプロイを分離する](0034-separate-release-and-worker-deployment.md)
- [Release 手順](../contributing/release.md)
