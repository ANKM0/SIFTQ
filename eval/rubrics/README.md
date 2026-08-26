# Rubrics

judge の判定基準・システムプロンプトを置く。

- `valid / borderline / invalid` の3段階に、見落とし検出を加える。
- 用途ごとに1つのrubricを持つ。複数用途を1つのrubricに混ぜない。
- judge自体は別モデルまたは人手と突合し、二値一致で信頼性を担保する。
