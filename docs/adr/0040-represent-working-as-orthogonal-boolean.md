# ADR 0040: 実施中を直交boolean workingで表す

## 決定

- 実施中は `status(do/done/skip)` と直交する boolean `Task.working` で表す。述語は `is_working` とし、`is_do/is_done/is_skip` と同形に揃える。
- `done/skip` へ遷移しても `working` は自動解除しない。1カードに1フラグを持ち、Matrix/一覧全体では複数の `working` が存在しうる。
- ソート(`sortForMatrix`)と既存の status 抽出・タブ切替は変えない。`working` の絞り込みは `filterTasks` の合成で行う。
- D1 では `working INTEGER NOT NULL DEFAULT 0 CHECK (working IN (0, 1))` で保持する。

### 決定の理由

- 実施中は完了ライフサイクルではなく `do` の下位状態(注目マーカー)であり、完了とは直交する軸のため。
- 既存の抽出・タブ・遷移・CHECK 制約への波及が列追加のみで済むため。
- `done/skip` 後の `working` 残存を許すことで、終了操作と注目解除を分離できるため。

## 不採用

- `status` の4値目(`doing`等)として表す方式
  - Matrix 抽出・一覧タブ・遷移・D1 CHECK の全てに波及し、`do` との下位関係を排他enumで表せないため。
- フィールド名 `active`
  - nav 状態(`Layout active`)と CSS(`.active`、`.is-active`)で使用中のため衝突するため。
- フィールド名 `focused` / `pinned`
  - 単一集中・表示固定を示唆し、複数許容・ソート不変の方針と衝突するため。

## 補足情報

### 背景

- ANKM0/SIFTQ#373 で Matrix / Task一覧の実施中表示を共有化する必要が生じた。

### 制約事項

- UI 詳細(ストライプ・ピル・右クリック+明示ボタン)は TBD の仮案であり、本 ADR の対象外。
- 表示文言(`working` / `実施中`)は実装時に選択する。

## 参考リンク

- [ADR 0026: Define task data model](0026-define-task-data-model.md)
- [ADR 0008: 更新競合には version 楽観ロックを採用する](0008-adopt-version-optimistic-locking.md)
