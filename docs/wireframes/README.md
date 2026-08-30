# SIFTQ UI Preview

このディレクトリは本番 Hono JSX component と CSS を固定モックデータで描画し、
wireframe 専用の状態とスタイルを重ねた静的 UI プレビューである。

## 生成

```sh
bun run docs:wireframes
```

`index.html` をブラウザで開いて各画面状態を確認する。画面内のリンクは静的プレビュー
内で遷移する。本番ヘッダーの上にある `UI Preview` は、この一覧へ戻るプレビュー専用の導線で
あり、本番UIの機能ではない。フォーム送信、HTMX 更新、DnD 永続化はこの出力では実行しない。

wireframe を変更したら、必ず再生成する。モックデータ、状態、wireframe 専用スタイルの正本は
[`scripts/generate-wireframes.ts`](../../scripts/generate-wireframes.ts) である。実アプリと異なる
wireframe 専用表現は、`src/` ではなくこの生成処理で管理する。

New task と Task detail は、同スクリプトの共通 editor テンプレートから生成する。画面ごとの差分は
タイトル、初期値、開く popover、操作ボタンだけである。

## 画面状態

- Matrix の各area余白 → `task-new-area-1.html` 〜 `task-new-area-4.html`
- 通常の New task → `task-new.html`（area 2）
- New task の Status／Area押下 → `task-new-status-menu.html`／`task-new-area-menu.html`
- New task の選択済み閉状態 → `task-new-status-selected.html`／`task-new-area-selected.html`
- Create結果 → `task-create-result.html`
- Task detail の通常／Status popover／Area popover → `task-detail.html`／`task-status-menu.html`／`task-area-menu.html`
- Matrix の各タスク → `task-detail-1-matrix.html`／`task-detail-2-matrix.html`（Cancel は Matrix へ戻る）
- Task list の各タスク → `task-detail-1.html` 〜 `task-detail-4.html`（Cancel は Task list へ戻る）
