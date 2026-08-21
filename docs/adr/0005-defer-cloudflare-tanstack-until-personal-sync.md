# ADR 0005: 個人向け自動同期まで Cloudflare/TanStack 採用を延期する

> Status: Superseded by [ADR 0007](0007-adopt-cloudflare-d1-as-system-of-record.md).

## 決定
<!-- 決定事項、採用した内容とその理由を記載 -->

- Cloudflare/TanStack の採用は、個人向け自動同期が必要になるまで延期する。
- MVP はローカル SPA として実装するが、将来的に Cloudflare/TanStackに移行する前提で実装を行う

### 決定の理由
<!-- 決定事項、採用した内容の理由を記載 -->

- MVP の目的はプロダクトを作ってみて最短で検証することであり、Cloudflareの導入は検証に必要な最小十分なタスクの範囲外だと判断したため

## 不採用
<!-- 採用しなかった内容とその理由を記載 -->

- MVP から Cloudflare/TanStack を採用する。
  - 検証に必要な最小十分な実装から外れるため却下。

## 補足情報

### 背景
<!-- 解決する問題の背景やチームの状況などの戦略。 -->

- MVP では、別端末や別ユーザーから同じ task データにアクセスする必要はない。
- 将来は自分の複数端末で task をほぼ自動同期する体験が必要になる見込みである。
- 個人向け自動同期が必要になった時点では、Cloudflare/TanStack を第一候補として再評価したい。
- Cloudflare/TanStack を MVP から採用すると、同期、認証、デプロイ、クラウド保存が中心機能に混ざる。

### 制約事項
<!-- ライブラリや設計の変更におけるトレードオフやできない事とその理由。 -->

- ローカル利用は必須である。
- MVP は単一ユーザー、単一ブラウザデータで成立させる。
- MVP では同期、認証、競合解決、削除同期、order 衝突、外部 API を扱わない。

## 参考リンク
<!-- ADRに関連する情報や参考にした資料へのリンク。 -->

- [Cloudflare React + Vite guide](https://developers.cloudflare.com/workers/framework-guides/web-apps/react/)
- [Cloudflare Workers local development](https://developers.cloudflare.com/workers/local-development/)
- [TanStack Start overview](https://tanstack.com/start/latest/docs/framework/react/overview)
