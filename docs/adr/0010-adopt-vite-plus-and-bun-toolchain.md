# ADR 0010: Vite+ と Bun を初期開発ツールチェーンとして採用する

## 決定

- Vite+ を開発、build、型検査、lint、format、test、Git hooks の窓口にする。
- Bun をパッケージマネージャとして `packageManager` に明示する。
- Turborepo と個別の hook / lint / format ツールの統合は初期導入しない。

### 決定の理由

- 単一アプリに必要な開発コマンドと設定を Vite+ に集約できる。
- Bun の依存管理を使いつつ、Vite+ の統一された開発ワークフローを利用できる。
- モノレポや追加のタスクオーケストレーションを先に持たずに済む。

## 不採用

- Vite、Oxlint、Oxfmt、Git hooks を個別に設定する。
  - 初期構成では設定と実行入口が分散するため。
- Turborepo を導入する。
  - 複数パッケージをまたぐビルドやキャッシュがまだ不要なため。

## 補足情報

### 背景

- 個人開発の初期段階では、開発ツールチェーンの選択肢を少なく保つ。

### 制約事項

- package manager の変更やモノレポ化が必要になった時は、この ADR を再評価する。
- Cloudflare Workers の実行環境は Bun ではなく Workers runtime である。

## 参考リンク

- [Vite+ guide](https://viteplus.dev/guide/)
- [Vite+ dependency management](https://viteplus.dev/guide/install)
- [Bun documentation](https://bun.sh/docs)
