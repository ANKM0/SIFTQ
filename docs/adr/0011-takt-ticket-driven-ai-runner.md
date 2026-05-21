---
codd:
  node_id: design:takt-ticket-driven-ai-runner-adr
  type: design
  status: accepted
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:taskfile-command-runner-adr
      relation: depends_on
      semantic: automation
  depended_by:
    - id: design:takt-ai-workflow
      relation: depends_on
      semantic: decision
---

# ADR 0011: TAKT for Ticket-Driven AI Runner

## Status

Accepted.

## Context

SIFTQの開発では、GitHub Issueを起点に、あらかじめ決めた手順でLLM agentに
実装、検証、PR作成を実行させるticket-driven AI development workflowを
導入したい。

このworkflowは、repositoryの既存規約であるbranch strategy、commit message
format、Taskfile command runner、CoDD validationを尊重する必要がある。また、
Codex subscription modelを使う前提のため、GitHub Copilot coding agentなどの
追加API課金を前提にしたSaaS中心の構成は初期候補から外す。

将来的には複数issueを並列実行する可能性がある。一方で、初期導入では
orchestrator全体を大きく作るより、1 issueに対するplan、implementation、
review、fix loopを小さく検証することを優先する。

## Decision

SIFTQの初期ticket-driven AI development runnerとしてTAKTを採用する。

TAKTは、GitHub Issueをtaskとして扱い、YAML workflowでplan、implement、
review、fixの流れを定義できるため、SIFTQの既存docsと`task ci`に沿った
実行手順を表現しやすい。

初期導入では、1 issueを手動または半自動でTAKTに投入し、isolated workspaceで
実行する。複数issueの同時実行が必要になった場合は、TAKTを置き換えず、
外側に薄いschedulerを追加する。schedulerはGitHub Issue labelを使って
`ai-ready`から`ai-running`へ状態を遷移させ、issueごとに`git worktree`を
作成し、各worktree内でTAKTを実行する。

TAKTはSIFTQ application runtimeの依存関係には含めない。導入対象は開発運用
workflowであり、React、Vite、Tauri target architecture、domain/application
codeには直接組み込まない。

## Rejected Alternatives

- Symphonyを初期runnerとして採用する: 複数agentや常駐orchestratorの設計思想は
  要件に近いが、現時点ではLinear前提が強く、GitHub Issues adapter、
  workspace lifecycle、Codex runner接続、retry、status reportingを含む基盤実装
  が初期導入として重い。複数issueの常時並列実行が主要要件になった段階で再検討
  する。
- SIFTQ repository内に`/symphony`をvendoringする: Symphonyはapplication module
  ではなく外部runnerまたはorchestration serviceとして扱うべきであり、SIFTQの
  application source treeへ混ぜると責務境界が曖昧になる。
- TAKTなしで独自runnerを先に実装する: GitHub Issue polling、worktree管理、
  Codex実行、PR作成を薄く作ることは可能だが、plan、implement、review、fix loop
  のworkflow表現まで自前で持つと初期検証の範囲が広がる。まずTAKTでworkflowを
  固め、必要な部分だけ外側に追加する方が小さく始められる。
- GitHub Copilot coding agent、Claude Code GitHub Actions、Devin、Factoryなど
  のhosted agent serviceを採用する: 導入は速いが、追加課金、service-specificな
  実行制約、ローカルでの制御性の低さがある。Codex subscription modelを中心に
  ローカル実行へ寄せたい初期方針とは合いにくい。
- OpenHands Resolverまたはmini-swe-agentを初期runnerにする: OSSでローカル実行
  しやすい候補だが、SIFTQがまず必要としているのはGitHub Issueを既存開発規約へ
  落とし込むworkflow runnerである。TAKTの方がticket-driven workflowとreview
  loopを小さく始めやすい。
- 最初から複数TAKT workerを常時並列化する: `git worktree`でfilesystem分離すれば
  可能だが、branch collision、dependency install cost、Codex同時実行制限、
  二重取得防止、PR競合の運用リスクがある。初期導入では同時実行1から始め、
  安定後にschedulerで`max_workers`を増やす。

## Consequences

- SIFTQはGitHub Issueを起点にしたAI実装workflowを、小さい導入範囲で検証できる。
- TAKT workflowには、branch strategy、commit message format、`task ci`、
  CoDD validation、unrelated fileを変更しない方針を明示する必要がある。
- 複数issueの並列実行はTAKT単体ではなく、将来追加するschedulerの責務として扱う。
- schedulerを追加する場合は、GitHub labelによるlocking、issueごとのbranch命名、
  worktree root、cleanup policy、failure reporting、PR作成手順を別途設計する。
- TAKT導入は開発運用の変更であり、SIFTQ application runtimeやproduct architecture
  には影響を与えない。
