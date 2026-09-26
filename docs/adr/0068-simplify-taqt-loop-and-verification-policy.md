# ADR 0068: taqt loop の簡略化と検証・再試行方針を定める

## 決定

- checker / post_review を廃止し、loop を implement → verification → fix の単一構造にする。
- verification の e2e はフロント変更を含む場合のみ実行し、それ以外は fast チェックで判定する。
- provider / tool の一時失敗は同一 step で設定回数まで再試行し、恒久失敗のみ human へ送る。
- loop の工程ごとにモデルと reasoning effort を設定で指定する。
- 検証対象は変更範囲から選択し、eval は arm と repetition を分離した workspace で並列実行する。

### 決定の理由

- review 構造の有無で完了率が改善せず、維持コストだけが残るため。
- フロント以外の変更に e2e は寄与せず、費用だけを増やすため。
- 一時失敗を human へ送ると自動修正の機会を失うため。
- モデル能力が完了率に効くため、工程ごとに適したモデルを選べるようにするため。
- 変更範囲外のチェックと逐次実行は費用対効果を下げるため。

## 不採用

- checker / post_review を維持する
  - 比較で完了率の改善が確認できないため。
- すべての変更で e2e を実行する
  - 非フロント変更の費用を増やすだけのため。
- 一時失敗も human へ送る
  - 再試行で回復する失敗を人の判断に委ねることになるため。

## 補足情報

### 背景

- ADR 0043 は loop を implement → verification → checker の単一構造に統一し、ADR 0067 が design step を廃止した。
- その後、checker / post_review の廃止、e2e の実行粒度、一時失敗の再試行、工程ごとのモデル指定が実施されたが、ADR に記録されていなかった。
- replay 集計は arm ごとの完了率/ human / cost / tokens を出していたが、human の原因内訳を持っていなかった。

### 制約事項

- 過去の run 記録と eval 結果は履歴として残し、削除しない。
- 本 ADR は既に実施した決定を記録するもので、決定自体は変更しない。

### 判断ごとの根拠と検証

| 検証ID | 判断・主張 | 根拠の種類 | 観測データ | データ充足条件 | 完了条件 | 許容できない結果 | 状態 | 再評価条件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V-068-001 | review 構造を外しても完了率は同等以上 | 比較実験 | eval の arm 別完了率と 人エスカレーション率 | 全 gold を repetition 3 以上で完走 | 簡略 arm の完了率が review arm 以上 | review arm が明確に上回る | 暫定 | 全量比較の完走または gold 更新時 |
| V-068-002 | 非フロント変更で e2e を省いても見逃し欠陥は 0 | 比較実験 | 非フロント変更 run の見逃し欠陥| 非フロント変更 run が蓄積 |見逃し欠陥が 0 |見逃し欠陥が 1 以上 | 暫定 | 検証対象や変更分類の変更時 |
| V-068-003 | 一時失敗の再試行で human 直行が減る | 観測 | provider / tool 失敗 run の再試行後の終端 | 一時失敗 run が蓄積 | 再試行で human 直行が減る | 再試行後も human が増える | 暫定 | 失敗種別や provider の変更時 |
| V-068-004 | 工程ごとのモデル指定で完了率が改善する | 比較実験 | 同一タスクのモデル別完了率| モデル別に repetition 3 以上 | 強いモデルで完了率が改善 | モデル間で差がない | 暫定 | モデルまたは工程構成の変更時 |
| V-068-005 | 変更範囲による検証選択と並列実行で費用が下がる | 観測 | 検証時間と実行コスト | 同一変更での before / after が取得できる | 費用が非悪化し見逃し欠陥が 0 | 費用増または見逃し欠陥が 1 以上 | 暫定 | 検証基盤または並列度の変更時 |

### 限界と再検討条件

- 限界: 比較実験は小標本で、完了率改善の有無を確定していない。human 原因内訳の分類精度も未検証。
- 再検討条件: 全量比較が簡略化の不利を示した場合、またはモデル・検証基盤・失敗種別が変わった場合。

## 参考リンク

- [ADR 0043: taqt loop を単一構造へ変更する](0043-unify-taqt-loop-execution-policy.md)
- [ADR 0058: モデルと provider を静的 profile で管理する](0058-use-static-model-provider-profiles.md)
- [ADR 0067: design step と design_notes を廃止する](0067-remove-design-step-and-design-notes.md)
- [Issue #561: loop 簡略化を ADR・eval・replay 集計に反映する](https://github.com/ANKM0/SIFTQ/issues/561)
- [loop 効果測定の結果](../../eval/results/loop/README.md)
- [loop 妥当性評価の基準](../../eval/loop-evaluation.md)
