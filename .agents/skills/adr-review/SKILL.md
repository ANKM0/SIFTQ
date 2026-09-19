---
name: adr-review
description: LLM-check SIFTQ ADRs for implementation details that belong in code or design docs. Use when authoring or revising an ADR, or when reviewing an ADR change.
---

# ADR Review (implementation detail check)

ADR は意思決定のみを記録する。実装詳細が混ざっていないかを LLM でレビューする。
決定論チェック（コードフェンス・source path）は `task -t .config/Taskfile.yml ci:adr` が担う。この skill は散文レベルの詳細を対象にする。

## When to use

- ADR を新規作成・変更したとき
- `adr-authoring` の最後
- taqt の checker が ADR 変更をレビューするとき

## Procedure

1. 対象 ADR を列挙する。新規採番された ADR、または今回変更した ADR のみ。
2. 各 section（決定 / 決定の理由 / 不採用 / 補足情報）の各項目を「意思決定」か「実装詳細」かに判定する。
3. 実装詳細と判定した箇所を `path:line: 理由` で列挙する。
4. 1 件でもあれば `verdict=changes_requested`、無ければ `verdict=approve` を返す。

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
