---
codd:
  node_id: design:taskfile-command-runner-adr
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:github-actions-ci-cd-toolchain-adr
      relation: depends_on
      semantic: ci
  depended_by:
    - id: design:issue-10-taskfile
      relation: depends_on
      semantic: decision
    - id: design:adr-index
      relation: depends_on
      semantic: index
---

# ADR 0009: Taskfile for Command Runner

## Status

Accepted.

## Context

SIFTQには、uv、pnpm、CoDD、GitHub Actionsで使う複数のローカルコマンドが
存在する。Issue #10では、それらを`task ...`から実行できるようにし、Codex
のallowリストにも登録することが求められている。

個別ツールの責務は既に分かれているため、task runnerは依存管理やbuild
systemを置き換えるものではなく、開発者とCIが使う入口を統一する薄い層で
ある必要がある。

## Decision

SIFTQのcommand runnerとしてTaskfileを採用し、`go-task/task`をaquaで
管理する。

`Taskfile.yml`には、setup、frontend、CI、CoDDの主要コマンドを定義する。
GitHub Actions CIでも、個別コマンドではなく`task ...`を優先して呼び出す。
Codex allowリストには、Taskfileで定義したtaskコマンドを個別に登録する。

## Rejected Alternatives

- npm scriptsのみ: frontendの範囲では自然だが、uvやCoDDなどrepository全体の
  コマンド入口としてはNode.js packageに寄りすぎる。
- Makefile: 汎用的で成熟しているが、Windowsを含む将来のローカルアプリ開発を
  見据えるとshell差分を吸収しにくい。
- shell scriptsのみ: 単純な処理には向くが、コマンド一覧、依存関係、説明文を
  一箇所で管理しにくい。
- just: task runnerとして有力だが、SIFTQではTaskfileの`desc`、task一覧、
  YAMLによる構造化、aquaでの導入しやすさを優先する。

## Consequences

- 開発者とCIが同じ`task ...`入口を使える。
- READMEやCodex allowリストのコマンド表現が短くなる。
- 個別ツールの詳細はTaskfileに集約される。
- Taskfileの変更時は、CI workflow、README、Codex allowリストとの同期を保つ
  必要がある。
