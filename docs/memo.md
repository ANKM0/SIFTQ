---
codd:
  node_id: design:codex-configuration-memo
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:command-permissions
      relation: depends_on
      semantic: permissions
    - id: design:sympohy-issue-execution
      relation: depends_on
      semantic: automation
---

# Codex configuration memo

調査日: 2026-06-20

## 目的

Codex 関連機能がこのプロジェクトでどこまで設定済みかを確認し、既存の
SIFTQ/Yoriwake プロジェクト構成と照合した結果を記録する。

## 参照した既存 project

- `README.md`: SIFTQ は React/TypeScript/Vite の local-first task matrix
  SPA。Issue-driven work には repo-local tooling の `sympohy` を使う。
- `docs/contributing/issue-execution.md`: `sympohy` は通常の Codex user
  config、`CODEX_HOME`、repository rules、repository skills に依存する。
- `docs/contributing/command-permissions.md`: LLM-assisted work 用の
  repository-local command permission rules は `.codex/rules/siftq.rules`。
- `Taskfile.yml`: `task ai:sympohy:*`、`task ci:*`、`task codd:*` などの
  Codex/sympohy/CI entrypoint が定義されている。

## 機能一覧

### 設定済み

| 機能 | 状態 | 根拠 |
| --- | --- | --- |
| Codex trusted project | 設定済み | `/home/develop/.codex/config.toml` に `[projects."/home/develop/Yoriwake"] trust_level = "trusted"` がある。 |
| `AGENTS.md` | 設定済み | repository root に `AGENTS.md` を追加。Codex 用の repo 共通ルール、skill 使い分け、検証方針を日本語で定義。 |
| Codex repo rules | 設定済み | `.codex/rules/siftq.rules` が存在し、read-only inspection、Git/GitHub、Taskfile、CoDD、禁止コマンドが `prefix_rule` で管理されている。 |
| Command permission CI | 設定済み | `Taskfile.yml` の `ci:lint:codex-task-perms` が Taskfile task と `.codex/rules/siftq.rules` の allow rule を照合する。 |
| sympohy hooks | 設定済み | `.sympohy/config.yaml` の `hooks` に `task ci` が定義されている。 |
| sympohy stage gate | 設定済み | `.sympohy/config.yaml` の `stage_gate_command` は `task ai:sympohy:stage-gate`。 |
| sympohy Codex model roles | 設定済み | `.sympohy/config.yaml` に `codex_model_<role>` / `codex_reasoning_<role>` を定義し、現アカウントで利用可能な `gpt-5.5` と `gpt-5.4-mini` を role ごとに割り当てている。 |
| sympohy automation commands | 設定済み | `Taskfile.yml` に `ai:sympohy`, `ai:sympohy:refine`, `ai:sympohy:resume`, `ai:sympohy:doctor`, `ai:sympohy:watch`, systemd 関連 task がある。 |
| sympohy systemd template | 設定済み | `.sympohy/systemd/sympohy-watch.service` がある。 |
| Codex invocation from automation | 設定済み | `scripts/sympohy/runner.py` は `codex exec` を呼び、`--ignore-user-config` や `--ignore-rules` を付けない設計。 |
| Repository skills under `.agents` | 設定済み | `.agents/skills/adr-authoring`, `feature-docs-planning`, `issue-implementation`, `self-improvement`, `adversarial-review`, `merge-readiness` がある。 |
| Repository skill under `.codex` | 設定済み | `.codex/skills/issue-creator` がある。 |
| Skill agent metadata | 設定済み | 各 skill に `agents/openai.yaml` がある。`self-improvement` は `interface:` キーなしで display metadata が直下定義。 |
| Global Codex skills | 設定済み | `/home/develop/.codex/skills/.system/` に system skills、`/home/develop/.codex/skills/grill-me` がある。 |
| Global plugins | 設定済み | `/home/develop/.codex/config.toml` で `gmail@openai-curated` と `github@openai-curated` が enabled。 |
| GitHub app approvals | 設定済み | `/home/develop/.codex/config.toml` で issue 作成/更新、PR 作成 tool が approval mode。 |
| Learning log | 設定済み | `.learnings/LEARNINGS.md`, `.learnings/ERRORS.md`, `.learnings/FEATURE_REQUESTS.md` がある。 |
| CoDD project graph | 設定済み | `.codd/codd.yaml`, `.codd/dag.json`, `.codd/scan/` があり、Taskfile に `codd:*` task がある。 |

### 未検出または未設定

| 機能 | 状態 | 根拠 |
| --- | --- | --- |
| `CLAUDE.md` | 未検出 | `/home/develop` 配下の浅い探索、および repository root の一覧で該当ファイルなし。 |
| Project-local Codex `config.toml` | 未検出 | repository 内には `.codex/config.toml` ではなく `.codex/rules/` と `.codex/skills/` がある。 |
| Active Git hooks | 未検出 | `.git/hooks` は `*.sample` のみ。project の verification hooks は Git hooks ではなく `sympohy` hooks として設定されている。 |
| Standalone Codex hook file | 未検出 | `hooks` は `.sympohy/config.yaml` に集約され、独立した Codex hooks 設定ファイルは見つからない。 |

## hooks の動作位置

`scripts/sympohy/runner.py` の実装では、Codex が logical step を実装した後に
`phase="hooks"` へ進み、`.sympohy/config.yaml` の hooks を順番に実行する。
現在の hooks は `task ci` のみ。hook が失敗した場合は Codex にログを読ませて
修正させ、再試行上限を超えると `sympohy:blocked` と `sympohy:phase:hooks` に
遷移する。

## doctor 検証結果

`task ai:sympohy:doctor` は成功した。確認された主な項目:

- `.sympohy/config.yaml`
- `default hook task ci`
- `stage gate command configured`
- `stage gate task declared`
- `systemd service template`
- `commit hook rejects invalid subject`
- `commit hook accepts repository subject`
- `required labels declared`
- `codex uses user config`
- `codex uses repo rules`

## まとめ

この project では、Codex の `AGENTS.md`、repository rules、repository
skills、global skills/plugins、sympohy hooks、stage gate、systemd watcher、
CoDD/CI 連携が設定済み。`CLAUDE.md`、project-local `.codex/config.toml`、
active Git hooks は未検出。verification hook は Git hook ではなく、
`sympohy` の Issue automation 内で `task ci` を実行する方式になっている。
