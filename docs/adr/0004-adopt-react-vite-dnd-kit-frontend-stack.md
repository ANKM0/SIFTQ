# ADR 0004: フロントエンドスタックとして React / Vite / dnd-kit を採用する

> Superseded by [ADR 0009](0009-adopt-hono-htmx-html-driven-ui.md).

## 決定
<!-- 決定事項、採用した内容とその理由を記載 -->

- フロントエンドは React で実装する。
- build / dev server は Vite を使う。
- Drag and drop は dnd-kit を使う。

### 決定の理由
<!-- 決定事項、採用した内容の理由を記載 -->

- React は client 側の状態管理、DnD 中の表示更新、将来の TanStack 移行に合うため。
- Vite は既存構成と一致し、Cloudflare Vite plugin や TanStack Start への将来移行にも合うため。
- dnd-kit は drag / drop / sort / reorder を扱いやすく、matrix の area / order 変更に向くため。

## 不採用
<!-- 採用しなかった内容とその理由を記載 -->

- htmx を UI スタックの中心にする。
  - htmx 自体は DnD ライブラリではなく、今回の中心機能では結局別の JavaScript が必要になるため却下。
- MVP から TanStack Start を採用する。
  - MVP では server functions、SSR、API routes が不要なため却下。

## 補足情報

### 背景
<!-- 解決する問題の背景やチームの状況などの戦略。 -->

- このプロジェクトの中心機能は、task を 4 象限の matrix 上で作成、表示、並び替え、移動することである。
- Matrix 上の drag and drop は、task の `area` と `order` を変更する主要操作である。
- htmx も候補に挙がったが、htmx は server-rendered HTML の差し替えや CRUD 画面に向く一方、DnD matrix のような client 側の細かい状態管理では、別の JavaScript 実装が主役になりやすい。

### 制約事項
<!-- ライブラリや設計の変更におけるトレードオフやできない事とその理由。 -->

- MVP では TanStack Start を採用しないが、将来移行を前提にフロントエンドスタックを選ぶ。
- MVP は browser 上で動く SPA として作る。
- DnD は mouse / touch / keyboard 操作と accessibility を考慮する。

## 参考リンク
<!-- ADRに関連する情報や参考にした資料へのリンク。 -->

- [Task Management 要求分析](../requirements/requirements-analysis.md)
- [dnd-kit documentation](https://docs.dndkit.com/)
- [htmx documentation](https://htmx.org/docs/)
- [Cloudflare React + Vite guide](https://developers.cloudflare.com/workers/framework-guides/web-apps/react/)
- [TanStack Start overview](https://tanstack.com/start/latest/docs/framework/react/overview)
