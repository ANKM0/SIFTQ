# LLM loop の決定論 checker 化

Issue #255 では、既存の readiness gate を LLM 起動前に維持する。readiness が不足する task は triage または human で終了し、design / test / implement を実行しない。

implement 後は `git diff --check`、fast lint/typecheck、変更範囲に応じた test、`task ci` をこの順で実行する。verification は最初の失敗で停止し、`pass`、`fix`、`human` の構造化結果と command、revision、changed paths を run artifact へ記録する。

Rv は verification が `pass` のときだけ readonly agent として起動する。Rv は `approve`、`changes_requested`、`human_required` の verdict を含む JSON を返す。post-Rv gate は JSON 契約と readonly 違反を検証し、approve を `done`、changes requested を fix、その他を human へ route する。

この契約は main と deepseek の development feedback loop に共通で適用する。
