# Loop baselines

paired replay (T3) の比較対象 (arm A) として使う loop 定義を置く。

- `main_loop_full_structure.yaml`: test-first の比較用 loop（test → implement → verification → checker）。実行時には使わず、新 loop との before/after 比較にのみ使う。design step は削除済み。
- 採用構成が確定したら本 README と基準値を `eval/baselines/` に記録する。
