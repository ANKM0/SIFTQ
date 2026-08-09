# Task Management Domain

## 目的

ユーザーから見える task の状態、属性、遷移ルールを外部設計として定義する。
ここでの domain は DB schema、ORM model、TypeScript の内部型定義ではない。

## Task

| 属性 | 値 | 外部仕様 |
| --- | --- | --- |
| `title` | text | matrix、list、detail に表示する。 |
| `description` | text | detail と new task で入力・編集する。 |
| `status` | `do` / `done` / `skip` | 進行状態。matrix 表示可否を決める。 |
| `area` | `1` / `2` / `3` / `4` | matrix の象限。常に保持する。 |
| `order` | number | area 内の表示順。 |

## Status

| Status | Matrix 表示 | List 表示 | 意味 |
| --- | --- | --- | --- |
| `do` | 表示する | 表示する | 実行対象の task。 |
| `done` | 表示しない | 表示する | 完了した task。 |
| `skip` | 表示しない | 表示する | 実行しない task。 |

## Area

- `area` は `1 / 2 / 3 / 4` のいずれかである。
- `area` は nullable にしない。
- `area` は matrix の象限を表す。
- `done` / `skip` の task も `area` を保持する。
- `status` を `do` に戻した場合は、保持している `area` に再表示する。

## 状態遷移ルール

- `status` と `area` は分離する。
- `status` を `done` または `skip` に変更しても `area` は変更しない。
- `area` 変更は detail の area popover から行う。
- `status` 変更は detail の status popover から行う。
- `status = do` の task だけが matrix に表示される。
- task list は `do / done / skip` の全 task を表示する。

## Order

- `order` は area 内の表示順を表す。
- matrix 上の drag and drop は task の `area` または `order` を変更する。
- 同じ area 内で並び替えた場合は `order` のみを変更する。
- 別 area へ移動した場合は `area` と移動先 area 内の `order` を変更する。
- `order` の永続化形式と正規化タイミングは次スコープで決める。
