# Task Management Screens

## 目的

0-base のタスク管理 UI の画面構成と画面遷移を外部設計として定義する。
この文書は画面から観測できる構造だけを扱い、内部実装方式は扱わない。

## 画面一覧

| id | 画面名 | 概要 |
| --- | --- | --- |
| P01 | Matrix | タスクを4象限のマトリックスでDnDする画面 (do statusのタスクのみを表示) |
| P02 | Task list | タスク一覧画面 全statusのタスクを表示する |
| P03 | Task detail | タスク詳細画面 title、description、status、area を確認・編集する |
| P04 | New task | 新規タスク作成画面 |
| P05 | Status popover | タスク詳細内のステータス選択パネル |
| P06 | Area popover | タスク詳細内のエリア選択パネル |

## 画面詳細

- `matrix-page.html`
  - `status = do` の task だけを表示する。
  - task は `area = 1 / 2 / 3 / 4` の象限に分けて表示する。
  - 縦軸は `重要度`、横軸は `緊急度` とする。
  - task card は title のみを表示する。
  - task card は matrix 上で drag and drop できる。

- `task-list.html`
  - 全 task を一覧表示する。
  - 各行は `#番号`、title、area badge、status badge を表示する。
  - area badge は `1 / 2 / 3 / 4` を表示する。
  - status badge は `do / done / skip` を表示する。

- `task-detail.html`
  - title と description を編集する。
  - status と area は右側 metadata として表示する。
  - `Cancel` は遷移前の一覧へ戻る。
  - `Save` は編集内容を保存する。

- `task-new.html`
  - detail と同じ 2 column layout を使う。
  - title と description を入力する。
  - status と area は右側 metadata として表示する。
  - 初期値は `status = do`、`area = 1` とする。
  - `Cancel` は一覧へ戻る。
  - `Create` は task を作成して detail へ進む。

- `task-status-menu.html`
  - detail 画面上で status 選択 popover を開いた状態を表す。
  - 選択肢は `do / done / skip` とする。
  - 完成 UI では同じ detail surface 上で開く。

- `task-area-menu.html`
  - detail 画面上で area 選択 popover を開いた状態を表す。
  - 選択肢は `1 / 2 / 3 / 4` とする。
  - 完成 UI では同じ detail surface 上で開く。

## 画面遷移

図の正本は Mermaid source の [`docs/requirements/assets/screen-flow.mmd`](assets/screen-flow.mmd) とする。
生成物は [`docs/requirements/assets/screen-flow.svg`](assets/screen-flow.svg) とする。
SVG は `pnpm run docs:screen-flow:svg` で再生成する。

[画面遷移図 SVG を開く](assets/screen-flow.svg)
