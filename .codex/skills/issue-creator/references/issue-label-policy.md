# SIFTQ Issue Label Policy

## Required automation labels

- `sympohy:pending`
  - sympohy が pick up する起動状態。
- `sympohy:phase:triage`
  - 新規 issue の初期実行フェーズ。

## Forbidden as manual assignment

- `sympohy:blocked`
- `sympohy:running`
- `sympohy:done`

これらは原則、sympohy が状態遷移として更新します。

## Optional labels

- 既存のプロジェクトラベル（機能種別、優先度など）があれば、内容に応じて追加可能。
- ラベルが存在しない場合は事前に追加せず、まずは上記2つのみで開始します。
