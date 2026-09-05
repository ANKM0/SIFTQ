---
name: mock-to-implementation
description: "Turn mock UI QA findings into confirmed requirements and scoped implementation work. Use when a UI is prototyped in src before BE, DB, or tests."
---

# Mock to Implementation

`src` のmock UIで操作感を確認し、QA結果から仕様変更を決め、確定した仕様を本実装へ引き継ぐフロー。

## Quick Reference

| Situation | Action |
|-----------|--------|
| mockのみ変更と言われた | 本スキルでmock-onlyの範囲を固定する |
| UI試作を始める | `src/components`、`src/styles.ts`、既存inline scriptのみ変更する |
| QA結果が出た | 見た目・操作・仕様・実装課題に分類する |
| 仕様変更を決める | ユーザー確認後に`docs/requirements`を更新する |
| 本実装へ進む | 実装計画を作り`issue-implementation`へ引き継ぐ |

## Background

UI仕様を詰める段階でBEまで作ると手戻りが大きい。
先にDOM操作だけのmockで操作感を固め、QAで決めた仕様を文書化してから永続化・競合・テストを実装する。

## Solution

### 許可範囲

- 変更可: `src/components/*`、`src/styles.ts`、`src/index.tsx` の表示部分、既存inline script文字列 (`MATRIX_*_SCRIPT` 等)。
- 変更不可: `src/task-repository.ts`、`src/preview/MemoryTaskRepository.ts`、`src/task.ts` のdomain、`migrations/*`、`tests/*`、`src/index.tsx` のAPI route (`/api/*`, `POST /tasks/*`) 新設・変更。

### Step-by-Step

1. **mockの対象と非対象を確認する**。対象画面、操作、固定データ、対象外のBE/DB/testを明記する。
2. **mock UIを作る**。表示側のDOM/CSSと既存inline scriptだけを変更し、永続化用の`fetch`やRepository変更は追加しない。
3. **ローカルpreviewを起動する**。`bun run preview:mock`で起動し、ログイン後に対象画面を確認する。
4. **UI QAを実施する**。正常操作、キャンセル、境界条件、画面外クリック、リロード後の初期状態を確認する。
5. **QA結果を分類する**。各指摘を「見た目」「操作」「外部仕様」「本実装課題」のいずれかに分類する。
6. **仕様変更案を作る**。外部から観測できる振る舞いだけを、画面仕様・ドメインルール・受け入れ条件に分けて記載する。
7. **ユーザーと仕様を確定する**。未決事項を一つずつ確認し、採用しない案も明記する。確認前にBE/DB/testを変更しない。
8. **requirementsを更新する**。確定した画面仕様は`docs/requirements/screens.md`、状態・削除・保持ルールは`domain.md`、要求とBDD候補は`requirements-analysis.md`へ反映する。
9. **mockと仕様の差分を整理する**。mock-onlyのDOM操作、未実装の永続化、競合、認可、order処理を引き継ぎメモにまとめる。
10. **本実装の変更単位を分解する**。domain、Repository、migration、API、画面、競合処理、unit/contract/e2e testの順に作業項目化する。
11. **本実装へ切り替える**。`issue-implementation`のブランチ・検証・コミット・PRフローへ引き継ぐ。
12. **mockを本実装へ置き換える**。成功時だけでなく、競合・エラー・キャンセル時の表示を確認し、mock-onlyの分岐を除去または本仕様に統合する。
13. **検証と文書を揃える**。最小テスト、e2e、`bun run preview:mock`または対象環境での確認を行い、BDD対応表と残課題を更新する。

### Code Example

```ts
// mockはDOM操作のみ。fetchもversion更新もしない。
card.remove();
```

## Gotchas

- リロードでmock状態は消える。`PREVIEW_TASKS` は固定初期データのままにする。
- `TaskCard` 全体がリンクのため、`contextmenu` では `preventDefault()` し、通常クリック/DnDと干渉させない。
- アクセシビリティを対象外とする仕様でも、対象外であることを`docs/requirements`に明記する。mockに一時的な`Esc`処理やARIA属性を入れた場合は、正式仕様との一致を本実装前に確認する。
- mockを本実装と誤認させない。PRやメモに `mock-only` と明記する。

## QA Record

QA結果は次の形式で残す。

```text
- 操作: task cardを右クリックしてdeleteを選択
- 観測: 中央に確認ダイアログが表示され、背後を操作できない
- 判断: 採用。screens.mdのP07へ反映
- 本実装: DELETE API、version競合、Repository削除、e2eを追加する
```

## Related

- `issue-implementation` スキル: 本実装のブランチ・コミット・PRフロー
- `docs/requirements/screens.md`: 画面の外部仕様
- `docs/requirements/domain.md`: status/areaの保持ルール

## Source

- Matrix done/skip/delete の仕様詰め (2026-09-05)。mock UIのQA結果をrequirementsへ反映してから本実装へ進む運用。
