# ADR(Architecture Decision Records)の一覧

## 一覧

| ADR | Status | Decision |
| --- | --- | --- |
| [ADR 0001: Skill による Repository Script の Orchestration](0001-skill-orchestrated-repository-scripts.md) | Accepted. | Skill は判断と orchestration、repository script は再現可能な操作、skill-local script は skill package 補助に限定する。 |
| [ADR 0002: ADR と Design Doc を分けて記録する](0002-separate-adr-and-design-docs.md) | Superseded by ADR 0012. | ADR と Design Doc を分けて記録していた。 |
| [ADR 0003: Task Management MVP の実装言語は TypeScript とする](0003-select-typescript-as-implementation-language.md) | Accepted. | 実装言語はTypeScriptを使用する。 |
| [ADR 0004: フロントエンドスタックとして React / Vite / dnd-kit を採用する](0004-adopt-react-vite-dnd-kit-frontend-stack.md) | Superseded by ADR 0009. | React、Vite、dnd-kit を採用していた。 |
| [ADR 0005: 個人向け自動同期まで Cloudflare/TanStack 採用を延期する](0005-defer-cloudflare-tanstack-until-personal-sync.md) | Superseded by ADR 0007. | Cloudflare/TanStack の採用延期を決定していた。 |
| [ADR 0006: アーキテクチャとして、軽量アプリケーションアーキテクチャを採用する](0006-adopt-lightweight-application-architecture.md) | Accepted. | Domain rule と入出力を分離しつつ、repository interface や storage adapter を先に作らない。 |
| [ADR 0007: Cloudflare D1 を唯一の正本 DB として採用する](0007-adopt-cloudflare-d1-as-system-of-record.md) | Accepted. | task データの唯一の正本は Cloudflare D1 とし、Worker を経由して操作する。 |
| [ADR 0008: 更新競合には version 楽観ロックを採用する](0008-adopt-version-optimistic-locking.md) | Accepted. | `version` による楽観ロックで競合を検出し、後勝ちは採用しない。 |
| [ADR 0009: Hono / HTMX による HTML 駆動 UI を採用する](0009-adopt-hono-htmx-html-driven-ui.md) | Accepted. | Hono JSX と HTMX を通常の UI、SortableJS を DnD に採用する。 |
| [ADR 0010: Vite+ と Bun を初期開発ツールチェーンとして採用する](0010-adopt-vite-plus-and-bun-toolchain.md) | Accepted. | Vite+ を開発ツールチェーン、Bun をパッケージマネージャに採用する。 |
| [ADR 0011: Resolve loop reasoning effort in Codex adapter](0011-resolve-loop-reasoning-effort-in-codex-adapter.md) | Accepted. | reasoning effort は step、agent、環境変数の順で解決し、指定時だけ Codex の config override に渡す。 |
| [ADR 0012: taqt 中心の loop engineering 実行方針](0012-adopt-taqt-centered-loop-engineering-policy.md) | Accepted. | Issue を要求の正本、taqt run を実行記録とし、外部連携を script adapter に分離する。 |
