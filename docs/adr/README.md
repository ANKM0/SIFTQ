# ADR(Architecture Decision Records)の一覧

## 一覧

| ADR | Status | Decision |
| --- | --- | --- |
| [ADR 0001: Skill による Repository Script の Orchestration](0001-skill-orchestrated-repository-scripts.md) | Accepted. | Skill は判断と orchestration、repository script は再現可能な操作、skill-local script は skill package 補助に限定する。 |
| [ADR 0002: ADR と Design Doc を分けて記録する](0002-separate-adr-and-design-docs.md) | Superseded by ADR 0012. | ADR と Design Doc を分けて記録していた。 |
| [ADR 0003: Task Management MVP の実装言語は TypeScript とする](0003-select-typescript-as-implementation-language.md) | Accepted. | 実装言語はTypeScriptを使用する。 |
| [ADR 0004: フロントエンドスタックとして React / Vite / dnd-kit を採用する](0004-adopt-react-vite-dnd-kit-frontend-stack.md) | Superseded by ADR 0009. | React、Vite、dnd-kit を採用していた。 |
| [ADR 0005: 個人向け自動同期まで Cloudflare/TanStack 採用を延期する](0005-defer-cloudflare-tanstack-until-personal-sync.md) | Superseded by ADR 0007. | Cloudflare/TanStack の採用延期を決定していた。 |
| [ADR 0006: アーキテクチャとして、軽量アプリケーションアーキテクチャを採用する](0006-adopt-lightweight-application-architecture.md) | Accepted. | Domain rule は構造体型・純粋関数・Result とし、interface は副作用境界に限定する。 |
| [ADR 0007: Cloudflare D1 を唯一の正本 DB として採用する](0007-adopt-cloudflare-d1-as-system-of-record.md) | Accepted. | task データの唯一の正本は Cloudflare D1 とし、Worker を経由して操作する。 |
| [ADR 0008: 更新競合には version 楽観ロックを採用する](0008-adopt-version-optimistic-locking.md) | Accepted. | `version` による楽観ロックで競合を検出し、後勝ちは採用しない。 |
| [ADR 0009: Hono / HTMX による HTML 駆動 UI を採用する](0009-adopt-hono-htmx-html-driven-ui.md) | Accepted. | Hono JSX と HTMX を通常の UI、SortableJS を DnD に採用する。 |
| [ADR 0010: Vite+ と Bun を初期開発ツールチェーンとして採用する](0010-adopt-vite-plus-and-bun-toolchain.md) | Accepted. | Vite+ を開発ツールチェーン、Bun をパッケージマネージャに採用する。 |
| [ADR 0011: Resolve loop reasoning effort in Codex adapter](0011-resolve-loop-reasoning-effort-in-codex-adapter.md) | Accepted. | reasoning effort は step、agent、環境変数の順で解決し、指定時だけ Codex の config override に渡す。 |
| [ADR 0012: taqt 中心の loop engineering 実行方針](0012-adopt-taqt-centered-loop-engineering-policy.md) | Superseded by ADR 0043. | Issue を要求の正本、taqt run を実行記録とし、外部連携を script adapter に分離する。 |
| [ADR 0013: worktree ごとの graphify 更新 Task](0013-worktree-scoped-graphify-update-task.md) | Accepted. | `task graphify:update` は worktree root を更新し、runtime 不在時は導入方法を含むエラーで止める。 |
| [ADR 0014: `repo:pull-main` の pull と graphify 更新](0014-repo-pull-main-guards.md) | Accepted. | main 以外または dirty worktree では pull せず、pull が成功して HEAD が更新された場合だけ graphify を更新する。 |
| [ADR 0015: 共有 Codex home とモデル profile](0015-worktree-scoped-codex-home.md) | Accepted. | skills・認証・session は `~/.codex` を共有し、モデルは静的 CLI profile、作業対象は worktree で分離する。 |
| [ADR 0016: worktree ごとの `git pull` 振り分け shell function](0016-worktree-scoped-git-pull-shell-function.md) | Accepted. | Yoriwake の interactive shell で、project worktree 内の引数なし `git pull` だけを `task repo:pull-main` へ振り分ける。 |
| [ADR 0017: `.learnings` を共有追跡成果物として維持する](0017-keep-learnings-tracked-as-shared-artifacts.md) | Accepted. | `.learnings/LEARNINGS.md` など 3 ファイルは追跡対象かつ PR レビュー・マージ対象のまま維持し、`.learnings/` は ignore しない。 |
| [ADR 0018: Adopt HTML-driven UI with JSON only for DnD](0018-adopt-html-driven-ui-with-json-only-for-dnd.md) | Accepted. | 画面・フォームは HTML 駆動、JSON は DnD 確定のみに限定する。 |
| [ADR 0019: Keep internal HTTP API private](0019-keep-internal-http-api-private.md) | Accepted. | API は公開せず内部 IF とし、HTML UI と `/api` を分離する。 |
| [ADR 0020: Adopt resource-oriented REST for internal API](0020-adopt-resource-oriented-rest-for-internal-api.md) | Accepted. | 内部 API にリソース指向 REST を採用し、BFF / RPC / GraphQL を採用しない。 |
| [ADR 0021: Define HTTP API contract conventions](0021-define-http-api-contract-conventions.md) | Accepted. | 内部 API の route / method / 成功レスポンスとバージョン方針を定める。 |
| [ADR 0022: Persist DnD through bulk reorder endpoint](0022-persist-dnd-through-bulk-reorder-endpoint.md) | Accepted. | DnD 永続化は一括 `POST /api/tasks/reorder` に分け、batch で原子的に更新する。 |
| [ADR 0023: Adopt RFC 9457 error body](0023-adopt-rfc9457-error-body.md) | Accepted. | JSON エラー body に RFC 9457 を採用し、code / message と項目単位エラーを分ける。 |
| [ADR 0024: Map errors to standard HTTP status codes](0024-map-errors-to-standard-http-status-codes.md) | Accepted. | エラーは標準 HTTP status にマップし、詳細は body の code で表現する。 |
| [ADR 0025: Define HTML and JSON error handling behavior](0025-define-html-and-json-error-handling-behavior.md) | Accepted. | HTML / JSON のエラー表現を分離し、内部エラー露出と 401 / 403 の共通挙動を定める。 |
| [ADR 0026: Define task data model](0026-define-task-data-model.md) | Accepted. | task の識別子・所有者・時刻・順序と D1 の型を定める。 |
| [ADR 0027: Adopt D1 SQL migration management](0027-adopt-d1-sql-migration-management.md) | Accepted. | Cloudflare 公式 SQL migration + Wrangler で schema を管理する。 |
| [ADR 0028: Adopt common UI state and feedback rules](0028-adopt-common-ui-state-and-feedback-rules.md) | Accepted. | 全画面の 4 状態と通知の表示時間・閉じ方を定める。 |
| [ADR 0029: Adopt Result type in domain and usecase](0029-adopt-result-type-in-domain-usecase.md) | Accepted. | domain / usecase は期待される失敗を inline union の `Result<T, E>` で返す。 |
| [ADR 0030: Adopt static component catalog](0030-adopt-static-component-catalog.md) | Accepted. | Hono JSX component を static HTML catalog 化し、Review 済み component を再利用する。 |
| [ADR 0031: Adopt Cloudflare Access for Worker access control](0031-adopt-cloudflare-access-for-worker.md) | Superseded by ADR 0032. | Worker の公開アクセス制御に Cloudflare Access を採用していた。 |
| [ADR 0032: Adopt Worker-managed shared-password authentication](0032-adopt-worker-managed-shared-password-authentication.md) | Accepted. | Worker 内の共有パスワード認証と署名付き Cookie でアクセスを制御する。 |
| [ADR 0033: md2idx は Bun の devDependency として導入する](0033-introduce-md2idx-as-bun-devdependency.md) | Accepted. | `md2idx` を `package.json` の devDependency で導入し、`bun x md2idx` で実行する。 |
| [ADR 0034: リリースと Worker デプロイを分離する](0034-separate-release-and-worker-deployment.md) | Accepted. | GitHub Release はリポジトリ変更、Worker デプロイは本番更新として分離し、変更種別で実施有無を判断する。 |
| [ADR 0035: 画面遷移図の生成ツールとして、D2を採用する](0035-adopt-d2-for-screen-flow-diagram.md) | Suspended by ADR 0044. | 画面遷移図の生成ツールとして、D2を採用する |
| [ADR 0036: Adopt Better Auth as future authentication migration target](0036-adopt-better-auth-as-future-auth-migration-target.md) | Accepted. | 将来のユーザー別認証・認可の移行先として Better Auth を採用し、当面は共有パスワード認証を維持する。 |
| [ADR 0037: LLMクライアントをcodexからopencodeに変更する](0037-switch-llm-client-to-opencode.md) | Accepted. | LLMクライアントをcodexからopencodeに変更する。 |
| [ADR 0038: Task一覧のページングにoffset方式を採用する](0038-task-list-offset-pagination.md) | Accepted. | Task一覧を25件固定のoffset分割とし、`?page=`で指定する。 |
| [ADR 0039: Task一覧のページングUIはGitHub issue一覧と同様にする](0039-task-list-pagination-ui.md) | Accepted. | ページ番号＋前へ/次へ、中間省略、status切替で1ページ目、一覧下のみ配置。 |
| [ADR 0040: 実施中を直交boolean workingで表す](0040-represent-working-as-orthogonal-boolean.md) | Accepted. | 実施中はstatusと直交するboolean `working`で表し、終了時も自動解除しない。 |
| [ADR 0041: Git の untracked ファイルを deny-by-default の path allowlist で管理する](0041-adopt-git-path-allowlist.md) | Accepted. | Git の untracked ファイルは path allowlist で明示的に許可し、生成物・作業状態・秘密情報は既定で拒否する。 |
| [ADR 0042: タスク編集draftをブラウザlocalStorageに保存する](0042-adopt-local-storage-task-edit-drafts.md) | Accepted. | 未保存のtitle / descriptionはブラウザのlocalStorageに一時draftとして保存し、D1はtaskの正本として維持する。 |
| [ADR 0043: taqt loop を単一構造へ変更する](0043-unify-taqt-loop-execution-policy.md) | Accepted. | taqt loop を `implement → verification → checker` の単一構造に統一し、limit 検知は human へエスカレーションする。 |
| [ADR 0044: Adopt single-source domain model JSON with generated diagrams](0044-adopt-single-source-domain-model-json.md) | Accepted. | ドメイン/データモデルの正本を `domain-model.json` に一本化し、D2 で図を生成する。`concept.d2` は廃止。 |
| [ADR 0045: Place logical-to-physical mapping in the generator](0045-place-logical-to-physical-mapping-in-generator.md) | Accepted. | 論理→物理の mapping は生成器のコードに置き、`migrations` を物理の正本として一致検証する。 |
| [ADR 0046: Track invariants with domain.md IDs and test names](0046-track-invariants-with-domain-md-ids-and-tests.md) | Accepted. | 不変条件は `domain.md` の `INV-TM-xxx` を正本とし、JSON は参照、テスト名に対応づけて検証する。 |
| [ADR 0047: Manage release version with git tags](0047-manage-release-version-with-git-tags.md) | Accepted. | バージョンの正本を git タグとし、`package.json` の `version` を削除する。リリースは release commit を作らず SHA にタグする。 |
| [ADR 0048: Discover aqua config in `.config/` through `.aqua/` symlinks](0048-discover-aqua-config-through-aqua-symlinks.md) | Accepted. | `.aqua/` symlink で `.config/` の aqua 設定を探索させ、bare の aqua コマンドを `AQUA_CONFIG` 無しで動かす。 |
