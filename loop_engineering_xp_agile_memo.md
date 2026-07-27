# メモ

業務仕様と実装使用は分ける
→ 実装使用はかき捨て, 業務仕様はドキュメントとして残す



業務仕様・プロダクト仕様
=> docs/requirements/<feature>.md

業務概念・状態・ルール・用語
=> docs/requirements/<domain-or-feature>.md
    または既存の docs/design/domain.md を将来的に requirements 側へ寄せる

BDD / executable examples
=> tests/bdd/ または tests/e2e/ / tests/unit/ のシナリオテスト
    ただし SSOT は docs/requirements 側

実装仕様・設計仮説
=> docs/design/<feature>.md
    実装後は archived / 破棄でよい

ADR
=> docs/adr/
    技術選定・境界・永続的な設計判断のみ



方針はこれです。

  要求分析ドキュメント
  - 要求 ID: なぜ必要か / ユーザーが達成したいこと
  - 仕様 ID: 外部から見える振る舞い / 受け入れ可能な条件
  - BDD ID: 仕様を確認する具体例

  ID の粒度はこう分けたいです。

  REQ-TM-001
  利用者は、実行すべきタスクを重要度と緊急度で整理したい。

  SPEC-TM-001
  実行対象のタスクは Matrix に表示される。

  SPEC-TM-002
  完了したタスクと見送ったタスクは Matrix から外れ、Task list には残る。

  BDD-TM-001
  完了したタスクは Matrix から消え、Task list には残る。

  ポイントは、要求 ID と仕様 ID を別物にすることです。

  要求 ID はユーザー価値・目的です。
  仕様 ID は観測可能な振る舞いです。
  BDD ID は仕様を確認する例です。
  実装 ID は原則作らなくていいです。実装は書き捨て設計・コード側で追えばよい。

  管理表はこういう形が扱いやすいです。

   ID             種別    内容                                                          親要求        BDD           状態
  ━━━━━━━━━━━━━  ━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━  ━━━━━━━━━━━━  ━━━━━━━━
   REQ-TM-001     要求    実行すべきタスクを重要度と緊急度で整理したい                  -             -             active
  ─────────────  ──────  ────────────────────────────────────────────────────────────  ────────────  ────────────  ────────
   SPEC-TM-001    仕様    実行対象のタスクは Matrix に表示される                        REQ-TM-001    BDD-TM-001    active
  ─────────────  ──────  ────────────────────────────────────────────────────────────  ────────────  ────────────  ────────
   SPEC-TM-002    仕様    完了・見送りのタスクは Matrix から外れ、Task list には残る    REQ-TM-001    BDD-TM-002    active

  BDD は仕様 ID を参照します。

  # BDD-TM-002
  # covers: SPEC-TM-002

  Scenario: 完了したタスクは Matrix から外れ、Task list には残る
    Given 実行対象のタスクが Matrix に表示されている
    When ユーザーがそのタスクを完了にする
    Then そのタスクは Matrix に表示されない
    And そのタスクは Task list に表示される

  このプロジェクトでの落としどころは、次です。

  docs/requirements/task-management-analysis.md
  - 要求分析の正本
  - REQ / SPEC / BDD の ID 管理
  - domain.md, screens.md, user-story-map.md から抽出した振る舞いを整理

  docs/design/domain.md
  docs/design/screens.md
  docs/design/user-story-map.md
  - 入力資料、外部設計、画面契約
  - 必要なら後で archive 可能

  tests/...
  - テスト名またはコメントで BDD-TM-xxx / SPEC-TM-xxx を参照

  結論: 要求分析ドキュメントを採用し、その中で REQ / SPEC / BDD ID を厳密管理する。USDM は全面採用ではなく、要求と仕様の階層管理だけ取り込むのがこの repo には合います。
