# ADR 0030: Adopt static component catalog for Hono JSX UI review

## 決定

- Hono JSX の再利用対象 component を pure な `(props) => JSX.Element` として `src/components/` に置く。
- component ごとに「状態 + props」の example を定義し、静的 HTML catalog を `docs/components/` へ生成する。
- Review は生成された static HTML と Playwright screenshot で行う。
- Review 済みの component だけを実装で import して再利用する。
- component catalog を LLM 実装時の参照元として扱う。
- Storybook は採用しない。

### 決定の理由

- Hono JSX は React ではないため、Storybook より HTML 文字列化した static catalog の方が render 経路が自然。
- Review 済み component を使い回すことで、LLM が毎回構造を推論する量と、見た目のばらつきを減らせる。
- static HTML はブラウザ・Git diff・Playwright のいずれでも確認しやすい。

## 不採用

- Storybook
  - 依存とビルドが増え、Hono JSX / HTMX との相性が悪いため。
- Worker 内に preview route を作る方式
  - 動的経路と本番コードが近くなり、Review 対象が安定しないため。

## 補足情報

### 背景

- ADR 0018 で UI は Hono JSX + HTMX の HTML 駆動を採用している。
- ADR 0028 で全画面の 4 状態を共通定義しているため、状態ごとの example を catalog に並べる。

### 制約事項

- catalog は static HTML とし、HTMX の動的挙動は Playwright E2E で検証する。
- component の見た目と props 契約は catalog を正とする。
- 導入後、catalog の生成・保守コストが再利用効果を上回る場合、または render 経路が実用に耐えない場合は本 ADR を廃止し、代替手段を再検討する。
- 廃止する場合は本 ADR を supersede する新 ADR を作成する。

## 参考リンク

- [ADR 0018: Adopt HTML-driven UI with JSON only for DnD](0018-adopt-html-driven-ui-with-json-only-for-dnd.md)
- [ADR 0028: Adopt common UI state and feedback rules](0028-adopt-common-ui-state-and-feedback-rules.md)
