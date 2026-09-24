# ADR 0067: design step と design_notes を廃止する

## 決定

- taqt loop から design step のサポートを廃止する。
- agent 応答の design notes から design artifact を生成する経路を廃止する。
- run report から design artifact の表示を廃止する。
- 比較用 baseline から design step を削除し、test-first 構造を残す。

### 決定の理由

- design artifact は生成されても消費されず、参照は run report の 1 行に限られるため。
- design notes による生成経路は ADR 0043 の移行後に記録がなく、実行時に発火していないため。
- design step は guard の write scope 逸脱の主要因として ADR 0043 で main_loop から廃止済みで、engine に残るサポートは比較 baseline 以外で使われていないため。
- 設計判断の参照は横断的な ADR と個別の PR で足り、専用 artifact を要しないため。

## 不採用

- design step を維持する
  - 実行時未使用で、機能か死にコードかの区別がつかないため。
- design notes を消費側に接続して復活させる
  - 設計判断の参照先は ADR と PR で足り、専用 artifact の消費者が存在しないため。

## 補足情報

### 背景

- ADR 0012 は design 判断を run artifact に保存する方針を定め、ADR 0043 は design step を廃止して implement の design notes に移した。
- しかし移行後、design artifact は記録されておらず、参照も run report の 1 行に限られる。

### 制約事項

- 過去の run に残る design artifact の記録は削除しない。run report の表示だけが汎用行になる。
- 比較用 baseline は test-first 構造として残し、design step のみを削除する。

### 判断ごとの根拠と検証

| 検証ID | 判断・主張 | 根拠の種類 | 観測データ | データ充足条件 | 完了条件 | 許容できない結果 | 状態 | 再評価条件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V-067-001 | design artifact は実行時に消費されていない | 観測 | design artifact を参照する経路の調査 | 実装全体の調査 | 参照経路が run report 以外に無い | 実装・レビュー・CI が design artifact を参照している | 確認済み | 新たな消費者が追加された時 |
| V-067-002 | design notes からの生成経路は移行後に発火していない | 観測 | run 記録の design artifact の由来 step の集計 | 移行後の run 記録が存在する | 移行後の design artifact が 0 | 移行後にも生成されている | 確認済み | run 記録が更新された時 |

### 限界と再検討条件

- 限界: design の思考効果そのものは測定していない。廃止は実行時未使用を根拠とする。
- 再検討条件: design artifact を消費する運用が新たに必要になった場合。

## 参考リンク

- [ADR 0012: taqt 中心の loop engineering 実行方針](0012-adopt-taqt-centered-loop-engineering-policy.md)
- [ADR 0043: taqt loop を単一構造へ変更する](0043-unify-taqt-loop-execution-policy.md)
- [Issue #525: taqt の未使用設定と重複処理を削除する](https://github.com/ANKM0/SIFTQ/issues/525)
