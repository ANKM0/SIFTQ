# Task Management 要求分析

## 目的

Task Management MVP の振る舞いを、要求 ID、仕様 ID、BDD ID で追跡できる
形に整理する。この文書は BDD シナリオの根拠となる要求分析の正本とし、
実装方式や内部設計は扱わない。

## 入力資料

- [Task Management Domain](domain.md)
- [Task Management Screens](screens.md)
- [ユーザーストーリーマップ](user-story-map.md)

## ID 管理

- `REQ-TM-xxx`: ユーザーが達成したいこと、またはプロダクト上の要求。
- `SPEC-TM-xxx`: 外部から観測できる振る舞い、状態、制約。
- `BDD-TM-xxx`: 仕様を具体例として確認するシナリオ。

## 要求

| ID | 要求 | 根拠 |
| --- | --- | --- |
| REQ-TM-001 | ユーザーは、実行対象のタスクを重要度と緊急度で整理したい。 | user-story-map.md, screens.md |
| REQ-TM-002 | ユーザーは、完了したタスクと見送ったタスクを Matrix から外しつつ、一覧では確認したい。 | domain.md, screens.md |
| REQ-TM-003 | ユーザーは、タスクの内容、状態、分類先を作成後に確認・編集したい。 | domain.md, screens.md |
| REQ-TM-004 | ユーザーは、Matrix 上でタスクの分類先と表示順を直接調整したい。 | domain.md, screens.md |
| REQ-TM-005 | 開発者は、固定データを使って本番 UI の操作をローカルで確認したい。 | screens.md |

## 仕様

| ID | 親要求 | 仕様 | BDD |
| --- | --- | --- | --- |
| SPEC-TM-001 | REQ-TM-001 | Task は title、description、status、area、order を持つ。 | BDD-TM-001 |
| SPEC-TM-002 | REQ-TM-001, REQ-TM-002 | 実行対象の Task は Matrix と Task list に表示される。 | BDD-TM-002 |
| SPEC-TM-003 | REQ-TM-002 | 完了した Task と見送った Task は Matrix に表示されず、Task list には表示される。 | BDD-TM-003 |
| SPEC-TM-004 | REQ-TM-001 | Matrix は Task を area ごとに 4 象限へ分けて表示する。 | BDD-TM-004 |
| SPEC-TM-005 | REQ-TM-003 | ユーザーは Task の title と description を作成・編集できる。 | BDD-TM-005 |
| SPEC-TM-006 | REQ-TM-003 | ユーザーは Task の status と area を detail から変更できる。 | BDD-TM-006 |
| SPEC-TM-007 | REQ-TM-002, REQ-TM-003 | status を完了または見送りに変更しても、Task の area は保持される。 | BDD-TM-007 |
| SPEC-TM-008 | REQ-TM-004 | Matrix 上の drag and drop は Task の area または area 内の order を変更する。 | BDD-TM-008 |
| SPEC-TM-009 | REQ-TM-004 | Matrix 上の drag and drop の永続化が競合した場合、表示をサーバー状態へ戻し、競合を通知する。 | BDD-TM-009 |
| SPEC-TM-010 | REQ-TM-005 | モック BE プレビューはログイン後に固定初期データを表示し、変更はプレビューの実行中だけ保持する。 | BDD-TM-010 |

## BDD 候補

| ID | 対象仕様 | シナリオ |
| --- | --- | --- |
| BDD-TM-001 | SPEC-TM-001 | Task を作成すると、表示と編集に必要な属性を持つ。 |
| BDD-TM-002 | SPEC-TM-002 | 実行対象の Task は Matrix と Task list の両方に表示される。 |
| BDD-TM-003 | SPEC-TM-003 | 完了した Task は Matrix から外れ、Task list には残る。 |
| BDD-TM-004 | SPEC-TM-004 | area が異なる Task は Matrix の対応する象限に表示される。 |
| BDD-TM-005 | SPEC-TM-005 | ユーザーは Task の title と description を保存できる。 |
| BDD-TM-006 | SPEC-TM-006 | ユーザーは detail から status と area を変更できる。 |
| BDD-TM-007 | SPEC-TM-007 | status を完了または見送りにしても、再び実行対象に戻すと元の area に表示される。 |
| BDD-TM-008 | SPEC-TM-008 | Task を別 area へ drag and drop すると、移動先 area に表示される。 |
| BDD-TM-009 | SPEC-TM-009 | Task を古い version で drag and drop すると、Matrix は最新状態へ戻り、競合が通知される。 |
| BDD-TM-010 | SPEC-TM-010 | モック BE プレビューにログインすると、固定初期データを Matrix と Task list で確認できる。 |

## 未決事項

- `Do`、`Done`、`Skipped` をユーザー表示名の正とするか、日本語表示名を正とするか。
- `area = 1 / 2 / 3 / 4` をユーザーに見せる分類名の正とするか、重要度・緊急度から導く名称を正とするか。
