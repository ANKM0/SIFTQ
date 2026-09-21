---
name: adr-review
description: LLM-check SIFTQ ADRs for implementation details and unsupported decision claims. Use when authoring or revising an ADR, or when reviewing an ADR change.
---

# ADR Review (implementation detail check)

ADR は意思決定と、その判断を支える根拠の要約を記録する。実装詳細の混入と、根拠・検証不足を LLM でレビューする。
決定論チェック（コードフェンス・source path）は `task -t .config/Taskfile.yml ci:adr` が担う。この skill は散文レベルの詳細を対象にする。

## When to use

- ADR を新規作成・変更したとき
- `adr-authoring` の最後
- taqt の checker が ADR 変更をレビューするとき

## Procedure

1. 対象 ADR を列挙する。新規採番された ADR、または今回変更した ADR のみ。
2. 各 section（決定 / 決定の理由 / 不採用 / 補足情報）の各項目を「意思決定」か「実装詳細」かに判定する。
3. 独立して間違え得る主張へ分解され、各主張に根拠の種類と確認範囲があるか確認する。
4. 性能・費用・使いやすさ・必要性・優劣などの経験的な主張に、同条件の比較検証があるか確認する。比較できない場合は暫定判断と限界が記載されていることを確認する。
5. 要件適合の確認を、代替案への優位性の根拠として扱っていないか確認する。
6. 検証結果の適用範囲を超えた主張、限界不足、再検討条件不足を確認する。
7. 実装詳細と判定した箇所、または根拠・検証不足の箇所を `path:line: 理由` で列挙する。
8. 1 件でもあれば `verdict=changes_requested`、無ければ `verdict=approve` を返す。

## 意思決定として許容

- 採用・不採用した技術、方式、境界（例: `localStorage`、D1 を正本、HTMX）
- 守る制約、不変条件、却下理由

## 実装詳細として違反

- キー名・変数名・関数名・型名などの識別子
- 数値の設定（TTL、上限、リトライ回数、順序）
- 処理順序やフックのタイミング（保存・削除の実行順など）
- コード片、コマンド、source path、ファイル名
- 具体的な API 呼び出しや内部データ構造

## Output

単一の JSON object を返す。

```json
{ "verdict": "approve", "findings": [] }
```
