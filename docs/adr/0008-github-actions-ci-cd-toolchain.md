---
codd:
  node_id: design:github-actions-ci-cd-toolchain-adr
  type: design
  status: draft
  depends_on:
  - id: design:pnpm-frontend-package-manager-adr
    relation: depends_on
    semantic: package-management
  depended_by:
  - id: design:taskfile-command-runner-adr
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
必要がある。Issue #6では、MVPをReact、TypeScript、Vite、dnd-kitによる
Browser SPAとして実装する方針を決定している。

CIは、現在のCoDD検証と`sympohy` automation設定検証を維持しつつ、v1
frontendのtypecheck、lint、test、buildを検証する必要がある。CDは、`v*`
タグからGitHub Releaseを公開できる最小構成にする。

## Decision

CI/CD基盤にはGitHub Actionsを採用する。

CIでは、aquaでrepository toolsを入れ、uvでPython/CoDD依存を入れ、pnpmで
frontend dependenciesを入れる。検証対象は、`sympohy` project
configuration、commit message、Markdown、TypeScript typecheck、ESLint、
Vitest、Vite build、CoDD version/scan/validate/dag verifyとする。

CDでは、`v*`タグpushまたは手動実行からGitHub Releaseを作成する。手動実行
では指定された`v*`タグを作成してpushし、そのタグからreleaseを作成する。

## Rejected Alternatives

- GitHub Actions以外のCIサービス: 現在のリポジトリ運用がGitHub Issues、
  Pull Request、GitHub Releasesを前提としているため、外部CI/CDサービスを
  追加する必要がない。
- Ruff、mypy、pytestを必須CIにする: v1 MVPの主要実装はReact/TypeScript/
  Viteであり、Python application codeはまだない。Python製support scripts
  が増えた段階で追加判断する。
- Rust/Tauriチェックを必須CIにする: 現行MVPはbrowser-only runtimeであり、
  Rust workspaceやTauri appを持たないため、不要なnative toolchain依存になる。

## Consequences

- Pull Requestでv1 frontendとCoDDの基本品質をまとめて検証できる。
- GitHub Releasesによる最小CDを、追加の外部サービスなしで運用できる。
- frontend実装が追加された時点から、TypeScript/ESLint/Vitest/Vite buildを
  CIゲートとして使える。
- Native appやRust workspaceを追加する場合は、別ADR/PRでCIゲートを拡張する。
