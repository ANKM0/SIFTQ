---
codd:
  node_id: design:github-actions-ci-cd-toolchain-adr
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:issue-6-matrix-mvp-tech-selection
      relation: depends_on
      semantic: tool-selection
    - id: design:pnpm-frontend-package-manager-adr
      relation: depends_on
      semantic: package-management
  depended_by:
    - id: design:issue-12-ci-cd
      relation: depends_on
      semantic: ci
    - id: design:taskfile-command-runner-adr
      relation: depends_on
      semantic: ci
    - id: design:issue-10-taskfile
      relation: depends_on
      semantic: ci
    - id: design:adr-index
      relation: depends_on
      semantic: index
---

# ADR 0008: GitHub Actions CI/CD Toolchain

## Status

Accepted.

## Context

Issue #12では、SIFTQにCI/CDを追加し、選定したツールをADRへ記録する
必要がある。Issue #6では、v1 MVPをReact、TypeScript、Vite、dnd-kitに
よるBrowser SPAとして実装し、v2以降でRustとTauriへ拡張する方針を決定
している。

CIは、現在のCoDD検証を維持しつつ、v1 frontendのtypecheck、lint、test、
buildを検証する必要がある。CDは、`v*`タグからGitHub Releaseを公開できる
最小構成にする。

## Decision

CI/CD基盤にはGitHub Actionsを採用する。

CIでは、aquaでrepository toolsを入れ、uvでPython/CoDD依存を入れ、pnpmで
frontend dependenciesを入れる。検証対象は、commit message、Markdown、
TypeScript typecheck、ESLint、Vitest、Vite build、CoDD version/scan/
validate/dag verifyとする。

CDでは、`v*`タグpushまたは手動実行からGitHub Releaseを作成する。手動実行
では指定された`v*`タグを作成してpushし、そのタグからreleaseを作成する。

## Rejected Alternatives

- GitHub Actions以外のCIサービス: 現在のリポジトリ運用がGitHub Issues、
  Pull Request、GitHub Releasesを前提としているため、外部CI/CDサービスを
  追加する必要がない。
- Ruff、mypy、pytestを必須CIにする: v1 MVPの主要実装はReact/TypeScript/
  Viteであり、Python application codeはまだない。Python製support scripts
  が増えた段階で追加判断する。
- Rust/Tauriチェックを今すぐ必須CIにする: Rust workspaceや`src-tauri/`が
  まだ存在しないため、v2以降の実装追加時に`cargo fmt`、`cargo clippy`、
  `cargo test`、Tauri buildを有効化する。

## Consequences

- Pull Requestでv1 frontendとCoDDの基本品質をまとめて検証できる。
- GitHub Releasesによる最小CDを、追加の外部サービスなしで運用できる。
- frontend実装が追加された時点から、TypeScript/ESLint/Vitest/Vite buildを
  CIゲートとして使える。
- Rust/TauriのCIゲートは、v2以降の実装追加時に別PRで拡張する必要がある。
