---
codd:
  node_id: design:pnpm-frontend-package-manager-adr
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:issue-6-matrix-mvp-tech-selection
      relation: depends_on
      semantic: tool-selection
  depended_by:
    - id: design:issue-12-ci-cd
      relation: depends_on
      semantic: tool-selection
    - id: design:github-actions-ci-cd-toolchain-adr
      relation: depends_on
      semantic: package-management
    - id: design:adr-index
      relation: depends_on
      semantic: index
---

# ADR 0007: pnpm for Frontend Package Management

## Status

Accepted.

## Context

Issue #6では、v1 MVPをReact、TypeScript、Vite、dnd-kitによるBrowser SPA
として実装し、v2以降でRustとTauriによるローカルアプリケーションへ進める
方針を決定している。Issue #12では、この技術選定に合わせてCI/CDで使用する
frontend toolchainを定義する必要がある。

frontend dependenciesは、ローカル開発とCIの両方で再現性を保つ必要がある。
また、将来`frontend/`、`src-tauri/`、shared packagesのように構成が分かれる
可能性があるため、workspace運用にも対応しやすいpackage managerを選ぶ。

## Decision

frontend package managerにはpnpmを採用する。

CIでは`pnpm-lock.yaml`を正とし、依存関係のinstallはlockfileに従って
再現可能に行う。`package.json`には`packageManager`を記載し、ローカル開発
とCIで同じpnpm系統を使う。

## Rejected Alternatives

- npm: Node.js標準で導入しやすいが、workspace運用とinstall性能の面でpnpmを
  優先する。v1 MVP後にfrontendやshared packagesが増える可能性を考えると、
  pnpmの方が依存関係の分離と再現性を扱いやすい。
- Yarn: 成熟した選択肢だが、Yarn classicとBerryで運用モデルが分かれる。
  このリポジトリでは新しいfrontend基盤を小さく始めたいので、追加の運用判断
  が少ないpnpmを優先する。
- Bun: install速度は魅力だが、現時点ではBun runtimeやBun testを採用する
  要件がない。v1 MVPはVite/Reactの標準的なNode.js ecosystemで十分であり、
  CIの安定性と一般的なTauri frontend運用を優先する。

## Consequences

- frontend依存関係は`pnpm-lock.yaml`で固定され、CIで再現しやすくなる。
- 将来workspace構成になった場合も、同じpackage managerで拡張しやすい。
- 開発者はNode.jsに加えてpnpmを利用できる環境を用意する必要がある。
- Bun固有の高速installやruntime機能は採用しない。必要になった場合は別ADRで
  再検討する。
