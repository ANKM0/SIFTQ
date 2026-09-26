# Loop baselines

paired replay (T3) の比較対象 (arm A) として使う loop 定義を置く。いずれも実行時には使わない。

- `main_loop_eval.yaml`: 簡略構造（implement → verification → fix）の eval クローン。
- `main_loop_eval_strong.yaml`: モデル比較用のクローン。checker / post_review 廃止に伴い簡略構造へ更新し、現状は `main_loop_eval.yaml` と同一構造・同一モデル。
- `main_loop_minimal.yaml`: 簡略構造の最小 loop（arm B）。

- 採用構成が確定したら本 README と基準値を `eval/baselines/` に記録する。
