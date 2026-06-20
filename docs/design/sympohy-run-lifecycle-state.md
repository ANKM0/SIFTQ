---
codd:
  node_id: design:sympohy-run-lifecycle-state
  type: design
  status: draft
  depends_on:
    - id: design:sympohy-ticket-driven-ai-runner-adr
      relation: depends_on
      semantic: decision
    - id: design:sympohy-issue-execution
      relation: depends_on
      semantic: automation
  depended_by:
    - id: design:sympohy-stale-run-recovery
      relation: depends_on
      semantic: lifecycle
---

# sympohy 実行ライフサイクル・状態設計

## 対象範囲

この設計書は、sympohy実行中issueのlabel、lock、run state、heartbeat、
worktree、phase lifecycleの境界を記録する。GitHub labelは外部から観測できる
issue lifecycleであり、`.sympohy/runs`とissueごとのworktreeはlocal execution
lifecycleである。

## 監視処理境界

`runner.py:watch`は、`github.py:list_candidate_issues`からopen issueを受け取り、
新規worker開始とstale実行復旧routingだけを判断する。新規issueは`run`をspawn
する前に、`sympohy:pending`と`sympohy:phase:triage`へ移動する。

`sympohy:pending`または`sympohy:running`を持つissueは、通常の新規実行として
再labelしない。staleと判定された場合だけ、`resume`経由の復旧対象にする。

## CLI境界

`cli.py`は、新規実行の`run`、中断またはstale実行の`resume`、AC/DoD確認の
`refine`、pollingの`watch`、GitHub label定義の`labels-sync`、local runner
前提条件確認の`doctor`を公開する。Taskfile entrypointは、これらのPython
commandを`uv run python -m scripts.sympohy`経由で呼び出す。

## ラベル境界

`core.py:transition_labels`は、既知の`sympohy` status labelとphase labelを
一度取り除いてから、要求されたstatusとphaseを追加する。これにより、sympohy
以外のlabelを保ちながら、activeなstatusとphaseをそれぞれ1つに保つ。

`scripts/sympohy/github.py:set_issue_state`は、最新のlabel集合を取得してから
remove/add差分を計算し、必要に応じて`gh issue edit --remove-label`と
`--add-label`を実行する。label transitionはこの経路に集約する。

## ロック境界

`runner.py:_IssueRunLock`は、issueごとに
`.sympohy/runs/issue-<number>/run.lock`を所有する。activeな並行実行を拒否し、
lock metadataとstate metadataが前回ownerのstale状態を示す場合だけtakeoverを
許可する。takeover後は、古いwriterがstateを更新できないようにする。

## 実行状態保存

runnerは、各issue runについて`.sympohy/runs/issue-<number>/state.json`を
書き込む。このstateには、共有`run_id`、現在phase、worker pid、heartbeat
timestamp、lock metadata、branch、worktree、plan参照、最後に把握した進捗、
最後のrecovery情報を含める。

Codex、hook、GitHub check、mergeなどの長時間subprocessが動作している間は、
heartbeat callbackでstateを更新する。これにより、GitHub labelとは独立した
stale判定用の永続signalを残す。

## フェーズライフサイクル境界

`run_issue`はtriageから開始し、AC/DoD完了後にimplementへ進む。各logical stepの
hook進捗を記録し、その後review、fix、mergeへ進む。blocking pathでは`_block`が
`sympohy:blocked`を付与し、logとworktreeを保持したまま、失敗phaseと原因を
commentする。

成功時は`runner`が`sympohy:done`を付与し、issueをcloseし、issue worktreeを
削除し、run logを保持する。

## 作業ツリー境界

`ensure_worktree`は、`.sympohy/worktrees/issue-<number>`を
`issue-<number>-sympohy` branch上に作成または復旧する。新規実行では既存のlocal
またはremote issue branchを拒否する。復旧時は期待branchを要求し、local/remote
stateのどちらからも安全に復旧できない場合はblockする。

## テスト観点

Python unit testは、candidate selection、stale inspection、resume routing、
lock takeover、run-state persistence、worktree recovery、implementation
recovery、terminal reconciliation、late-phase dirty worktree blockingを対象に
する。TypeScript workflow contract testは、Taskfile、CLI、stale-running、
run-state、Codex configのcontractをfrontend test suiteから見える状態に保つ。
