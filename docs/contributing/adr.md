# ADR

## 目的

意思決定の理由 (Why) を残す。

判断は、将来ほかの判断とは独立して撤回・変更でき、継続して参照するものをADRに記録する。局所的な判断は、PR・Issue・コード・テスト・実験記録に残す。

ADRでは、独立して間違え得る主張ごとに根拠の種類と確認範囲を記載する。性能・費用・使いやすさ・必要性・優劣などの経験的な主張には比較検証を行い、検証できない場合は未検証の暫定判断とする。

未確認の主張には、観測データ、データ充足条件、完了条件、状態、再検討条件を補足情報に記載する。未確認の観点は `docs/adr/README.md` の検証待ち表で一元管理し、後段の評価は `adr-verification` skill で任意に起動する。

## 手順

- Path: `docs/adr/<four-digit-number>-<decision-title-in-kebab-case>.md`
- Template: `.agents/templates/adr.md`
- Script: `uv run python scripts/create_adr.py --title "..." --slug "..." --dry-run`

1. 次の 4 桁番号を採番する。
1. template の placeholder を埋める。
1. `docs/adr/README.md` に追加する。

## レビュー

- 実装詳細が混ざっていないかを確認する。ADR には意思決定のみを書き、識別子・設定値・処理順序・コード・コマンド・source path は code か design doc に置く。ただし、参考リンクに置く検証証拠への参照は許容する。
- 各主張の根拠、検証範囲、限界、再検討条件を確認する。比較検証が必要な主張を根拠の記載だけで確定扱いしない。
- 未確認の主張に観測データ、データ充足条件、完了条件、状態があることを確認する。データ不足とNGを混同しない。
- 決定論チェック: `task -t .config/Taskfile.yml ci:adr`（新規採番 ADR のコードフェンスと source path を検出）。
- 散文レビュー: `adr-review` skill（LLM）で実装詳細、根拠不足、比較検証不足、過大な主張を列挙し、`changes_requested` の指摘を解消する。
- 後段検証: `adr-verification` skill（LLM）でデータ充足を確認し、詳細結果を実験記録へ保存して、READMEの検証待ち表を更新する。完了した観点は検証待ち表から削除する。

## 更新

- 既に Accepted の ADR の決定・理由は書き換えない。検証契約は補足情報に残し、結果は実験記録に保存する。決定を変更する場合は `> Status: Superseded by [ADR XXXX](...).` を先頭に付し、新しい決定を新規 ADR として起こす。
