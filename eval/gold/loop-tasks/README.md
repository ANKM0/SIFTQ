# タスクリプレイ gold（T3）

ループ変更の closure と escaped defect をタスク単位で測る。`run_loop` は GitHub に書き込まないため、リプレイに副作用はない。

## gold タスク

マージ済み PR を持つ過去タスクを選ぶ。正解はその PR の diff とテスト。

- `.taqt/tasks/*.yaml` の `status: done` と closed issue を出典にする。
- 学習汚染を避けるため、モデルの学習カットオフ以降のタスクや非公開タスクを優先する。
- 難易度・領域を本番分布に寄せる。
- 初期 10〜20 件、目標 30+。

## リプレイ spec

`eval/gold/loop-tasks/<name>.yaml`:

```yaml
name: ISSUE-123
arms:
  A: .taqt/loops/main_loop.yaml
  B: .taqt/loops/quick_loop.yaml
checks:
  - task ci:test:unit
```

- `arms`: arm 名 → loop 定義パス。
- `checks`: loop が `done` のときに実行する held-out 検査。fail なら escaped defect と数える。

## 実行

```bash
uv run python -m loop_eval.replay --spec eval/gold/loop-tasks/<name>.yaml --task .taqt/tasks/<ISSUE>.yaml --repo .
```

arm ごとの status 集計（closure rate）と escaped rate を JSON で出力する。

## 判定

主指標は arm ごとの closure rate と escaped rate。arm 間の比較は同一タスク・同一基準 commit で行う。非決定性のため各タスク R ≥ 3 回繰り返し、点推定と n を併記する。小標本で有意性を主張しない。
