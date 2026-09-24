# Task and Idea Management Domain

## 目的

ユーザーから見える task の状態、属性、遷移ルールを外部設計として定義する。
ここでの domain は DB schema、ORM model、TypeScript の内部型定義ではない。

## Task

| 属性 | 値 | 外部仕様 |
| --- | --- | --- |
| `title` | `Title` 値オブジェクト | matrix、list、detail に表示する。 |
| `description` | `Description` 値オブジェクト | detail と new task で入力・編集する。http/https URL は編集領域内でリンクとして表示するが、保存値はプレーンテキストとする。 |
| `status` | `do` / `done` / `skip` | 進行状態。matrix 表示可否を決める。 |
| `area` | `1` / `2` / `3` / `4` | matrix の象限。常に保持する。 |
| `order` | number | area 内の表示順。 |

## Idea

- `Idea` は `Task` と独立したエンティティである。
- `title` は Task と共有する `Title` 値オブジェクトを使う。
- `description` は Task と共有する `Description` 値オブジェクトを使う。
- 属性は `title`、`description`、`order`、`pinned` とする。
- `order` の昇順でカード表示する。
- `pinned = true` のカードを先に表示し、その中で `order` の昇順にする。
- `pinned` はカードの固定状態を表す。
- Idea は作成、編集、削除、ピン留め、並べ替えを行う。

## Title

- `title` は Task と Idea が共有する `Title` 値オブジェクトである。
- 内包する値は text である。
- `title` の長さは、Unicodeコードポイント数で1以上256以下とする。

## Description

- Task と Idea の `description` は、同じ `Description` 値オブジェクトである。
- 内包する値は text である。
- 空文字を許可する。
- `description` の長さは、Unicodeコードポイント数で0以上16,384以下とする。
- 保存値はプレーンテキストとする。

## Status

| Status | Matrix 表示 | List 表示 | 意味 |
| --- | --- | --- | --- |
| `do` | 表示する | 表示する | 実行対象の task。 |
| `done` | 表示しない | 表示する | 完了した task。 |
| `skip` | 表示しない | 表示する | 実行しない task。 |

## Area

- `area` は `1 / 2 / 3 / 4` のいずれかである（INV-TM-007）。
- `area` は nullable にしない。
- `area` は matrix の象限を表す。
- `done` / `skip` の task も `area` を保持する。
- `status` を `do` に戻した場合は、保持している `area` に再表示する。

## 不変条件

実装とテストが守るべき不変条件。ID は `domain-model.json` の `rules` から参照し、テスト名にも含める。

| ID | 不変条件 |
| --- | --- |
| INV-TM-001 | `status` は `do` / `done` / `skip` のいずれかである。 |
| INV-TM-002 | `status` を `done` または `skip` にしても `area` を保持する。 |
| INV-TM-003 | `working` は `status` と直交し、終了時も自動解除しない。 |
| INV-TM-004 | `order` は `owner_id + area` 内で連番を保つ。 |
| INV-TM-005 | `title` の長さはUnicodeコードポイント数で1以上256以下とする。 |
| INV-TM-006 | `description` の長さはUnicodeコードポイント数で0以上16,384以下とする。 |
| INV-TM-007 | `area` は `1 / 2 / 3 / 4` のいずれかである。 |

## 状態遷移ルール

- `status` と `area` は分離する。
- `status` を `done` または `skip` に変更しても `area` は変更しない。
- `area` 変更は detail の area popover から行う。
- `status` 変更は detail の status popover から行う。
- `status = do` の task だけが matrix に表示される。
- task list は選択した status の task だけを表示する。選択肢は `do / done / skip` とし、初期値は `do` とする。
- task list の status 選択は再表示可能な状態として扱い、`/tasks?status=<status>` で保持する。

## Delete

- task の delete は status 変更ではなく、task 自体の完全削除である。
- delete した task は Matrix、Task list、detail のいずれにも表示しない。
- delete した task は復元しない。

## Order

- `order` は area 内の表示順を表す。
- matrix 上の drag and drop は task の `area` または `order` を変更する。
- 同じ area 内で並び替えた場合は `order` のみを変更する。
- 別 area へ移動した場合は `area` と移動先 area 内の `order` を変更する。
- `order` の永続化形式と正規化タイミングは次スコープで決める。
