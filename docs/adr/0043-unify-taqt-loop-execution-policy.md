# ADR 0043: taqt loop を単一構造へ変更する

> Status: Partially superseded by [ADR 0067](0067-remove-design-step-and-design-notes.md).

## 決定

- taqt loop を `implement → verification → checker` の単一構造に統一し、design / test step を廃止する。
- design step の判断は implement agent の応答（`design_notes`）から `artifacts/design-decision.md` を生成して保存する。
- モデルの limit / rate-limit を検知したら自動切替（fallback）せず、human へエスカレーションする。
- verification の失敗は分類せず `fix` へ決定論的に routing し、`max_fix_attempts` 超過で human とする。
- 結果ガード（危険コマンド禁止、readonly reviewer、worktree 分離、監査、verification gate）は維持する。

### 決定の理由

- design step は guard の write scope 逸脱の最大要因（計測で 43 件中 36 件）で、強モデルには摩擦が net の害になる。
- 検証は verification に e2e を加えて強化済みで、独立レビューは readonly の checker が担う。
- fallback は単一モデルを役割を問わず差し替えるため design が降格し、挙動も非決定的になる。limit は人手判断に回す方が安全。

## 不採用

- design / test step の維持
  - write scope 逸脱が集中し、強モデルへの摩擦が実測で net の害になる。
- 自動 fallback
  - 役割の能力を落とし、実行経路が非決定的になる。
- per-task loop 選択
  - 単一 loop では選択肢がなく、task の `loop:` は実行に使われていない。
- 複数モデルセットの loop 併存
  - 自動切替をしない前提では役割が重複する。

## 補足情報

### 背景

- #255 の決定論 verification gate 導入時に、失敗を分類して責任 step へ戻す producer が `verification` step に置換され、`decide` の routes 契約が更新されなかった。結果、verification 失敗が全件 human に落ちていた。
- #413 で軽量な `quick_loop` が追加されたが、標準化はされていなかった。

### 制約事項

- GitHub Issue を要求の正本とする方針は維持する。
- ADR 0037（opencode client）は維持する。

## 参考リンク

- [ADR 0012: taqt 中心の loop engineering 実行方針](0012-adopt-taqt-centered-loop-engineering-policy.md)
- [ADR 0037: LLMクライアントをcodexからopencodeに変更する](0037-switch-llm-client-to-opencode.md)
