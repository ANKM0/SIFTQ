---
codd:
  node_id: design:sympohy-stale-run-recovery
  type: design
  status: draft
  depends_on:
    - id: design:sympohy-run-lifecycle-state
      relation: depends_on
      semantic: lifecycle
    - id: design:sympohy-ticket-driven-ai-runner-adr
      relation: depends_on
      semantic: decision
    - id: design:sympohy-issue-execution
      relation: depends_on
      semantic: automation
---

# sympohy 停滞実行復旧設計

## 対象範囲

この設計書は、sympohyの`sympohy:running`監視処理、停滞実行検出、
再開経路、復旧時の実装phase再開境界を記録する。label、lock、state、
worktreeの通常ライフサイクルは
`docs/design/sympohy-run-lifecycle-state.md`で扱う。

## 候補選択

`scripts/sympohy/github.py`は、次の形でopen issueを取得する。

```text
gh issue list --state open --limit <limit> --json number,title,state,labels
```

その後、filteringを`scripts/sympohy/core.py:is_candidate_issue`へ委譲する。
現在のpredicateは、sympohy status labelを持たないopen issueを新規作業として
受け入れる。terminalな`sympohy:blocked`と`sympohy:done`は除外し、
`sympohy:pending`または`sympohy:running`は`inspect_running_issue`がstale stateを
返した場合だけ再選択する。

## 停滞判定

stale inspectionは、存在しないstate、壊れたstate、存在しないphase、存在しない
pid、停止済みpid、存在しないheartbeat、期限切れheartbeatを復旧可能なstale signal
として扱う。stale thresholdは`stale_status_after_minutes`で設定し、
`sympohy doctor`が正の値として検証する。

`.sympohy/runs/issue-<number>/state.json`が利用できる場合、GitHub labelよりも
local stateを優先する。stateが存在しない、または壊れている場合だけ、phase labelを
fallback bootstrap inputとして扱う。

## 監視処理の復旧経路

watcherは、新規issue開始と停滞実行復旧を分離する。新規open issueには
`sympohy:pending`と`sympohy:phase:triage`を付与してから`run` workerを開始する。
停滞した`sympohy:running` issueは、既存のrunning labelとphase contextを保ったまま
`resume` entrypointへdispatchする。

## 再開地点解決

`resume`は、run stateが存在する場合は`state.json.phase`から粗いresume pointを
解決する。`triage`はplanning、`implement`と`hooks`はimplementation recovery、
`review`、`fix`、`merge`はphaseごとのlate-phase handlerに対応する。

terminal status labelは再起動しない。`sympohy:blocked`はblocked terminal point、
`sympohy:done`はcompleted terminal pointとして解決する。

## 実装フェーズ復旧

停滞実行復旧がimplementationへ戻る場合、runnerはまず既存の
`.sympohy/runs/issue-<number>/plan.json`を読み込む。有効な保存済みplanがあれば、
新しいplanを生成せずに再利用し、logical step番号をrestart前後で安定させる。

runnerはlocal Git stateから完了済み作業を推定する。commit subjectが
`#<issue> feat(sympohy): implement logical step <n>`に一致するcommitは、
configured base branch上で連続したprefixに含まれる場合だけ完了済みlogical step
として扱う。

そのprefix判定後にworktreeへ未commit変更が残っている場合、runnerはその変更を次の
logical stepの作業だと推測せず、operator inspectionのためにblockする。

worktreeがcleanな場合は、同じ連続commit prefixから次のactionを決める。未完了の
implementationが残っている場合は次のlogical stepからCodexを再開する。保存済みplanの
logical stepがすべてcommit済みであれば、implementationをskipしてbranch pushと
draft PR作成へ進む。

## 既存テスト

`tests/sympohy/sympohy_core_test.py`は、`sympohy:running` issueのstale-running
inspection、candidate selection、`transition_labels`によるstatus/phase置換を
coverする。

`tests/sympohy/sympohy_runner_test.py`は、新規issueとstaleな`sympohy:running` issue
それぞれのwatcher dispatch、dirty/clean implementation resume decisionをcoverする。

`tests/sympohy/sympohyWorkflowContracts.test.ts`は、stale-running inspection、
run state persistence、resume entrypointに関するstring-level watcher contractを
保持する。
