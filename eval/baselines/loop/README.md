# Loop baselines

paired replay (T3) の比較対象 (arm A) として使う loop 定義を置く。

- `main_loop_full_structure.yaml`: #427 以前の design / test 付き main loop。実行時には使わず、新 loop との before/after 比較にのみ使う。
- 採用構成が確定したら本 README と基準値を `eval/baselines/` に記録する。
