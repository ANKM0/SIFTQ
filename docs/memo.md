# コードレビュー観点メモ

## 目的

LLM / 人間レビューを減らし、レビュー観点を「ルール＋テスト＋閾値」へ移す。
対象はプロジェクト全体（`src/` / `scripts/` / `.taqt/` / `docs/`）。
仕様は別成果物として持たず、テスト・型・ルールで担保する。

## 観点

| # | 観点 | 自動化方針 | 主なツール |
| --- | --- | --- | --- |
| 1 | 仕様・要件の充足 | テスト＝仕様、型／バリデーション＝仕様、ルール＝仕様。要件IDとテストの対応を checker で確認 | Vitest / zod（追加） / ESLint / check_requirements.py |
| 2 | バグ・エッジケース・境界値 | 既知パターンは ESLint。未知の境界はプロパティ／境界値テスト。BDDは追加せず `describe` / `it` 名で Given-When-Then を表現 | ESLint / Vitest / fast-check（追加） |
| 3 | 設計・レイヤー責務・局所化 | レイヤー境界・依存方向・循環依存を禁止 | dependency-cruiser（追加） / knip / ESLint |
| 4 | 命名・コメントの業務適合 | 用語集を正とし、表記ゆれ・禁止語・必須コメントを lint | ESLint / textlint（追加） / 用語集 |
| 5 | セキュリティ判断 | secret・依存脆弱性・taint・危険APIを検出。allowlist は設定で管理 | gitleaks / pnpm audit / eslint-plugin-security / Semgrep（追加） |
| 6 | テスト網羅性・品質 | coverage 閾値・命名規則・要件ID対応・mutation testing | Vitest coverage / Stryker（追加） |
| 7 | 性能の許容判断 | 既知パターンを lint。bundle size・クエリ上限・実行時間を予算で判定 | ESLint / wrangler build / 自作 rule |
| 8 | ドキュメント更新の要否 | 変更種別→ドキュメント対応表で更新漏れを検出 | check_docs.py / changesets（追加） |

仕様そのものの正しさは自動検知できない。人間は要件レビューとルール追加に限定する。

## 実装方針

- 8観点を「ルール＋テスト＋閾値」で `task ci` に落とす。
- 新設タスク: `ci:requirements` / `ci:architecture` / `ci:glossary` / `ci:security` / `ci:performance` / `ci:docs`。
- 高速 lint: `ci:lint:python`（ruff）と `ci:lint:ts-fast`（oxlint）を `ci` と loop に含める。
- loop の `observe` に追加し、`checker` 前段で実行する。
- ツール選定: 既存・高速ツールを優先する。TS/TSX は Biome / oxlint、Python は ruff で代用できるルールを置き換え、残りを ESLint / `scripts/ci/` で補う。
- 言語構成: AST 系ルールは TypeScript、リポジトリ横断チェックは Python。TS 一本化はしない。
- ルール配置:
  - ESLint (`eslint.config.js`): 構文・命名・禁止API
  - Python checker (`scripts/ci/check_*.py`): リポジトリ横断・要件ID対応
  - 設定 (`taskfile/core.yml` / `knip.json` / `.jscpd.json`): 実行定義・閾値
- テスト粒度:
  - Vitest: 関数・ルート・境界値単位。正常・境界・異常を1ケースずつ。
  - Playwright: ユーザー操作・画面遷移単位。1受入基準=1テスト。
- 計測目標（初回 SLO）:
  - 変更ファイルのみの lint: 5秒以内
  - 全ファイル lint: 15秒以内
  - ローカル `task ci`: 2分以内
  - CI `task ci`: 5分以内（依存 install 除く）
- 既存ツール優先。既存で代替できない狭い差分のみ自作する。
- 各ルールに根拠・削除条件・ignore条件・テストを付ける。
- ルール未定義の新規ケースはその場でレビューせず、ルール追加として切り出す。
