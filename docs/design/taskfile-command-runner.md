---
codd:
  node_id: design:taskfile-command-runner
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:command-permissions
      relation: depends_on
      semantic: permissions
    - id: design:github-actions-ci-cd-toolchain-adr
      relation: depends_on
      semantic: ci
    - id: design:taskfile-command-runner-adr
      relation: depends_on
      semantic: decision
---

# Taskfile コマンドランナー設計

## 背景

Taskfile command runnerでは、SIFTQで`task`コマンドを使用できるようにし、既存の
`uv run ...`、frontend setup、CI系コマンドを`task ...`から実行できるように
することが求められている。あわせて、定義したtaskコマンドをCodexのallow
リストに登録する必要がある。

## 概要

Taskfileを導入し、ローカル開発、CI、CoDD検証の入口を`task`に集約する。
個別ツールは引き続きaqua、uv、pnpmで管理し、Taskfileはそれらを置き換えず
実行入口だけを統一する。

## 対象範囲

- `go-task/task`をaqua管理ツールに追加する。
- `Taskfile.yml`を追加し、setup、frontend、CI、CoDDのタスクを定義する。
- GitHub ActionsのCI workflowで、可能な限り`task ...`を使う。
- READMEのローカル実行手順を`task ...`中心に更新する。
- `.codex/rules/siftq.rules`に定義済みtaskコマンドをallowとして追加する。
- Taskfile選定のADRを追加する。

## 対象外

- task以外のtask runner導入。
- CI/CD workflow全体の再設計。
- frontend実装やCoDD仕様の変更。
- Codexの禁止ルール緩和。

## タスク対応表

| task | 実行command |
| --- | --- |
| `task setup` | `task setup:python` and `task setup:frontend` |
| `task setup:python` | `uv sync --all-groups` |
| `task setup:frontend` | `pnpm install` |
| `task setup:frontend:ci` | `pnpm install --frozen-lockfile` |
| `task ci` | local CI gate |
| `task ci:commit-messages` | `uv run python scripts/ci/check_commit_messages.py` |
| `task ci:markdown` | `uv run python scripts/ci/check_markdown.py` |
| `task ci:typecheck` | `pnpm typecheck` |
| `task ci:lint` | `pnpm lint` |
| `task ci:test` | `pnpm exec playwright install chromium`, `pnpm test`, `task pytest`, and a Playwright E2E preflight that skips locally when Chromium runtime libs are unavailable while still failing in CI |
| `task ci:build` | `pnpm build` |
| `task frontend:dev` | `pnpm dev` |
| `task codd:version` | `uv run codd version --check` |
| `task codd:scan` | `uv run codd scan` |
| `task codd:validate` | `uv run codd validate` |
| `task codd:dag` | `uv run codd dag verify` |
| `task codd:elicit` | `uv run codd elicit` |

## 受け入れ条件

- `aqua install`で`task`コマンドが利用できること。
- 既存の主要なsetup、frontend、CI、CoDDコマンドを`task ...`で実行できる
  こと。
- GitHub Actions CIでtask定義を利用していること。
- `.codex/rules/siftq.rules`にTaskfileで定義したtaskコマンドがallowとして
  記録されていること。
- CoDD検証が通ること。
