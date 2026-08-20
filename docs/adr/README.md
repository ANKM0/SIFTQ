# ADR(Architecture Decision Records)の一覧

## 一覧

| ADR | Status | Decision |
| --- | --- | --- |
| [ADR 0001: Skill による Repository Script の Orchestration](0001-skill-orchestrated-repository-scripts.md) | Accepted. | Skill は判断と orchestration、repository script は再現可能な操作、skill-local script は skill package 補助に限定する。 |
| [ADR 0002: ADR と Design Doc を分けて記録する](0002-separate-adr-and-design-docs.md) | Accepted. | ADR は横断的な意思決定、Design Doc は機能や設計検討を記録する文書として分ける。 |
| [ADR 0003: Task Management MVP の実装言語は TypeScript とする](0003-select-typescript-as-implementation-language.md) | Accepted. | 実装言語はTypeScriptを使用する。 |
| [ADR 0004: フロントエンドスタックとして React / Vite / dnd-kit を採用する](0004-adopt-react-vite-dnd-kit-frontend-stack.md) | Accepted. | フロントエンドは React、build/dev server は Vite、drag and drop は dnd-kit を使う。 |
| [ADR 0005: 個人向け自動同期まで Cloudflare/TanStack 採用を延期する](0005-defer-cloudflare-tanstack-until-personal-sync.md) | Accepted. | Cloudflare/TanStack は MVP では採用せず、個人向け自動同期が必要になった時点で再評価する。 |
| [ADR 0006: アーキテクチャとして、軽量アプリケーションアーキテクチャを採用する](0006-adopt-lightweight-application-architecture.md) | Accepted. | Task Management MVP は domain rule と入出力を分離しつつ、MVP では repository interface や storage adapter を先に作らない。 |
