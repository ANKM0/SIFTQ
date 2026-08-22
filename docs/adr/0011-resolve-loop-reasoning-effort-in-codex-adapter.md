# ADR 0011: Resolve loop reasoning effort in Codex adapter

## 目的
<!-- 解決したい課題はXXX。 -->

loop 定義から Codex の reasoning effort を一貫して解決し、実行時の設定へ渡す規則を定める。

## 背景
<!-- 解決する問題の背景やチームの状況などの戦略。 -->

loop YAML は agent / step 単位の設定を持つが、`reasoning_effort` の解決規則がなく、Codex adapter へ渡せなかった。複数の loop で同じ挙動を再利用できる契約が必要になった。

## 制約事項
<!-- ライブラリや設計の変更におけるトレードオフやできない事とその理由。 -->

- 既存 loop で effort を指定しない場合の挙動を変えない。
- 対象は Codex adapter とし、他の adapter の契約は変更しない。
- 許可値は `none`、`low`、`medium`、`high`、`xhigh`、`max` に限定する。

## 内容

### 採用した内容
<!-- 採用した内容とその理由を記載 -->

- `reasoning_effort` は step、agent、`LOOP_CODEX_REASONING_EFFORT` の順で解決し、すべて未指定なら Codex の既定値に委ねる。
  - step 単位の上書きを可能にしつつ、agent 単位と環境変数による既定値も維持できるため。
- 解決値がある場合だけ Codex command に `-c model_reasoning_effort=<value>` を渡す。
  - 未指定時に不要な override を追加せず、既存の Codex 既定動作を維持できるため。
- agent と llm step の `reasoning_effort` は schema で許可値を検証する。
  - 実行時ではなく loop 定義の検証時に誤記を検出できるため。

### 採用しなかった内容
<!-- 採用しなかった内容とその理由を記載 -->

- 任意の文字列をそのまま Codex に渡す。
  - loop 定義の誤記を早期に検出できないため。
- 環境変数だけで effort を指定する。
  - step / agent 単位の設定を表現できないため。

## 影響範囲
<!-- ADRの決定が及ぼす可能性のある影響範囲。 -->

- `.taqt/scripts/loop/schema.py`
- `.taqt/scripts/loop/llm.py`
- `.taqt/tests/loop_engineering_test.py`

## 参考リンク
<!-- ADRに関連する情報や参考にした資料へのリンク。 -->

- [Issue #165](https://github.com/ANKM0/SIFTQ/issues/165)
