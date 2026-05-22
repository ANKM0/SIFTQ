---
codd:
  node_id: design:issue-12-ci-cd
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:codd-adoption
      relation: depends_on
      semantic: verification
    - id: design:commit-message-format
      relation: depends_on
      semantic: workflow
    - id: design:issue-6-matrix-mvp-tech-selection
      relation: depends_on
      semantic: tool-selection
    - id: design:pnpm-frontend-package-manager-adr
      relation: depends_on
      semantic: tool-selection
    - id: design:github-actions-ci-cd-toolchain-adr
      relation: depends_on
      semantic: ci
---

# Issue 12 CI/CD Design Proposal

## Background

Issue #12では、SIFTQにCIとCDを定義し、選定したツールをADRに記録することが求められている。現在のリポジトリには、CoDDのみを実行するGitHub
Actionsワークフロー、uvで管理するPython依存関係、aquaで管理するCLIインストール、コミットメッセージ形式の規約、ADR作成ルールが既に存在する。
Issue #6では、v1 MVPをReact、TypeScript、Vite、dnd-kitによるBrowser
SPAとして実装し、v2以降でRustとTauriによるローカルアプリケーションへ進める方針を決定している。

## Summary

リポジトリの自動化をCoDDのみのチェックからCI/CDの基本形へ拡張し、Pull
Requestの検証とバージョンタグからのGitHub Release作成を行えるようにする。

## Scope

- 現在のCoDD専用ワークフローを、`push`と`pull_request`で実行されるCIワークフローに置き換える。
- ツールのインストール方法は、既存のaqua、uvに加え、frontend用のNode.js package managerに合わせる。
- コミットメッセージ形式、Markdown、TypeScript、ESLint、Vitest、Vite build、CoDDのチェックを追加する。
- v2以降でRust/Tauri実装が追加された段階で、`cargo fmt`、`cargo clippy`、`cargo test`、Tauri build検証を追加する。
- `v*`タグからGitHub Releaseを作成するリリースワークフローを追加する。
- 手動実行時に注釈付きの`v*`タグを作成し、そのタグからリリースを公開できるようにする。
- CI/CDツール選定の判断を記録するADRを追加する。
- CIで実行されるコマンドに対応するローカル実行手順を、READMEまたはcontributingドキュメントに記載する。

## Out Of Scope

- パッケージやコンテナイメージの公開。
- 実行環境へのデプロイ。
- GitHubリポジトリ設定でのブランチ保護変更。
- デフォルトの`GITHUB_TOKEN`を超えるシークレット管理。
- CoDDを別のトレーサビリティシステムへ置き換えること。

## Acceptance Criteria

- `.github/workflows/`配下にCIワークフローが存在し、`push`と`pull_request`で実行されること。
- CIにコミットメッセージlint、Markdown lint、TypeScript typecheck、ESLint、Vitest、Vite build、CoDD検証が含まれていること。
- Rust/TauriのCIチェックは、v2以降でRust workspaceまたはTauri appが追加された段階で有効化できる設計になっていること。
- `.github/workflows/`配下にCDワークフローが存在し、`v*`タグからGitHub Releaseを公開できること。
- CDワークフローが手動実行時にリリースタグを作成できること。
- `docs/adr/`配下のADRに、GitHub Actions、aqua、uv、選定したlint/type/testツールを使う理由が記録されていること。
- CIチェックに対応するローカル実行コマンドがドキュメントに記載されていること。
- 設計ドキュメントとADRを追加したあと、CoDD検証が通ること。

## Definition Of Done

- 人間の承認後、実装変更がIssue用ブランチにコミットされていること。
- `task setup:python`が成功すること。
- frontend依存関係のinstallが成功すること。
- 実装ブランチのコミット範囲に対してコミットメッセージlintが成功すること。
- リポジトリ内のMarkdownファイルに対してMarkdown lintが成功すること。
- TypeScript typecheckが成功すること。
- ESLintが成功すること。
- Vitestが成功すること。
- Vite buildが成功すること。
- `task codd:validate`が成功すること。
- `task codd:scan`が成功すること。
- `task codd:dag`で新しいブロッキング失敗が発生しないこと。
- `main`向けのドラフトPull Requestが作成されていること。

## Expected Files And Areas

- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `.github/workflows/codd.yml`
- `package.json`
- `pnpm-lock.yaml`
- `pyproject.toml`
- `uv.lock`
- `scripts/ci/`
- `tests/docs/markdownCiContract.test.ts`
- `src/`
- `tests/`
- `frontend/`
- `src-tauri/`
- `docs/adr/`
- `docs/adr/README.md`
- `docs/requirements/system-requirements.md`
- `README.md`

## CoDD Impact

実装では、CoDDの`design:`ノードを持つADRを追加し、`docs/requirements/system-requirements.md`からリンクする。新しいCIゲートを満たすためだけに補助スクリプトやスモークテストを追加する場合、それらが長期的なプロダクト挙動にならない限り、個別のCoDDノードは不要とする。

## Implementation Notes

- v1 MVPではfrontend実装にNode.js ecosystemが必要になるため、CIでもfrontend dependenciesをinstallして検証する。
- frontendのpackage managerは、lockfileによる再現性を優先してpnpmを第一候補にする。
- TypeScript typecheck、ESLint、Vitest、Vite buildは`package.json`のscriptsに集約する。
- コミットメッセージとMarkdownのチェックは、frontend依存に強く結合させず、リポジトリ全体の運用チェックとして実行する。
- Ruff、mypy、pytestはv1 MVPの主要スタックではないため、Python製のapplication codeまたはsupport scriptsが追加されるまで必須CIにはしない。
- Rust/Tauriのチェックはv2以降で`src-tauri/`またはRust workspaceが追加された段階で有効化する。
- パッケージやイメージ公開の要件が出るまでは、リリースワークフローの対象をGitHub Releasesに限定する。
- CIでは`contents: read`を使い、`contents: write`はリリースワークフローだけで使う。
- Markdown CIの生成物除外契約は`tests/docs/markdownCiContract.test.ts`で固定する。

## Suggested Issue Split

最初のCI/CDベースラインとしてはIssue分割は不要とする。リリース成果物、パッケージ公開、ブランチ保護が必要になった場合は、別のフォローアップIssueを作成する。
