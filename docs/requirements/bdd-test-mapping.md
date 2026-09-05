# BDD テスト対応表

`docs/requirements/requirements-analysis.md` の BDD シナリオと検証の対応を示す。

| BDD | テストファイル | 対象 |
| --- | --- | --- |
| BDD-TM-001 | `tests/bdd/task-api.contract.test.ts` / `tests/bdd/task-domain.contract.test.ts` | POST /api/tasks と domain の task 生成 |
| BDD-TM-002 | `tests/bdd/task-api.contract.test.ts` / `tests/bdd/task-domain.contract.test.ts` | task list と matrix の do 抽出 |
| BDD-TM-003 | `tests/bdd/task-api.contract.test.ts` / `tests/bdd/task-domain.contract.test.ts` | done / skip の list 残存と matrix 除外 |
| BDD-TM-004 | `tests/bdd/task-domain.contract.test.ts` | area ごとの matrix グループ化 |
| BDD-TM-005 | `tests/bdd/task-api.contract.test.ts` | PATCH /api/tasks/{id} |
| BDD-TM-006 | `tests/bdd/task-api.contract.test.ts` / `tests/bdd/task-domain.contract.test.ts` | status / area 変更 |
| BDD-TM-007 | `tests/bdd/task-domain.contract.test.ts` | status 変更時の area 保持 |
| BDD-TM-008 | `tests/bdd/task-api.contract.test.ts` / `tests/bdd/task-domain.contract.test.ts` | reorder |
| BDD-TM-009 | `tests/bdd/task-api.contract.test.ts` | 競合時の 409 + code |
| BDD-TM-010 | `tests/preview.test.ts` | モック BE プレビューの固定初期データ |
| BDD-TM-011 | `tests/e2e/matrix.spec.ts` / `tests/bdd/task-dnd.contract.test.ts` | Matrix右クリックmenuの表示 |
| BDD-TM-012 | `tests/e2e/matrix.spec.ts` | Matrixからdoneへのstatus変更 |
| BDD-TM-013 | `tests/e2e/matrix.spec.ts` | Matrixからskipへのstatus変更 |
| BDD-TM-014 | `tests/e2e/matrix.spec.ts` | delete確認のキャンセルとoverlay |
| BDD-TM-015 | `tests/e2e/matrix.spec.ts` / `tests/bdd/task-api.contract.test.ts` | delete確定後のtask除外 |
| BDD-TM-016 | `tests/bdd/task-ui.contract.test.ts` / `tests/e2e/matrix.spec.ts` | Task listのstatus filter、初期値、空状態、再読み込み後の選択状態 |

repository 契約は `tests/bdd/task-repository.contract.test.ts` で
`TaskRepository` の in-memory double を使い、insert / list / find / update /
remove / move の契約を固定する。
