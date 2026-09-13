# architecture

このプロジェクトで使用するアーキテクチャについて定義

## アーキテクチャについて

- [小規模から成長させるアプリケーションアーキテクチャ](https://note.com/suwash/n/n869c06c749e6) をもとにして、
- 不要な抽象化や層分割を避け、副作用の境界だけに最小限の interface を置く軽量な sh アーキテクチャを採用する。
- domain は構造体型、純粋関数、`Result<T, E>` で実装し、DB、HTTP、Hono、`Date`、`crypto` などの副作用 API に依存しない。
- 依存方向は presentation → usecase → domain とし、domain から presentation や repository adapter へ依存しない。
- repository interface は usecase と副作用の境界に必要な場合だけ定義し、repository adapter は factory function と object literal で実装する。
- アプリケーション固有の class と、将来の差し替えだけを目的とした interface は作らない。

### interface の利用箇所

- `src/task-repository.ts` の `TaskRepository` は、D1 と preview の各 adapter が実装する副作用境界の契約である。
- `src/index.tsx` では、Hono の binding へ repository を注入し、handler が D1 の実装へ依存しないためにだけ利用する。
- `src/preview/MemoryTaskRepository.ts` とテストの in-memory double は、同じ契約を満たす adapter として利用する。
- domain の `src/task.ts` には interface を置かず、repository、DB、HTTP、時刻、乱数などの副作用へ依存させない。

詳細は以下を参照
  - [`docs/contributing/assets/app-architecture.mmd`](assets/app-architecture.mmd)
  - [`docs/contributing/assets/app-architecture-layers.svg`](assets/app-architecture-layers.svg)

### アーキテクチャ図

- 図の正本は Mermaid source の [`docs/contributing/assets/app-architecture.mmd`](assets/app-architecture.mmd) とする。
- 生成物は [`docs/contributing/assets/app-architecture.svg`](assets/app-architecture.svg) とする。
- SVG は `bun run docs:app-architecture:svg` で再生成する。
- 4レイヤー概念図は [`docs/contributing/assets/app-architecture-layers.svg`](assets/app-architecture-layers.svg) を正本とする。
- 図中の `domain` は構造体型・純粋関数・`Result`、`repository` は副作用境界の最小 interface、`adapter` は factory function + object literal を表す。

![軽量アプリケーションアーキテクチャの4レイヤー](assets/app-architecture-layers.svg)

![軽量アプリケーションアーキテクチャ](assets/app-architecture.svg)
