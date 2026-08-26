# BDD テスト対応表

Issue #196 で追加する契約テストと `docs/requirements/requirements-analysis.md`
の BDD シナリオとの対応を示す。

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

repository 契約は `tests/bdd/task-repository.contract.test.ts` で
`TaskRepository` の in-memory double を使い、insert / list / find / update /
move の契約を固定する。
