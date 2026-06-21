---
codd:
  node_id: design:development-flow
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:sympohy-issue-execution
      relation: depends_on
      semantic: automation
---

# 開発フロー

図の正本は [`docs/contributing/assets/development-flow.mmd`](assets/development-flow.mmd) とする。

## 実装フェーズの PR 作成タイミング

実装フェーズでは、`main` を最新化して issue branch を作成した直後に、その
branch を `origin` へ push し、`main` 向け draft PR を作成する。

この draft PR は実装途中の traceability と review / CI の受け皿であり、最終
実装完了後に初めて作成するものではない。実装 commit、hook fix commit、review
fix commit、final verifier fix commit は、すべて同じ PR branch に追加 push
する。

branch 作成直後に差分がまだ無い場合、automation は PR 作成用の空 commit を
許可してよい。ただし commit message は
[`commit-message-format.md`](commit-message-format.md) に従い、関連 issue
番号を含める。

## 全体図

![開発フロー](assets/development-flow.svg)
