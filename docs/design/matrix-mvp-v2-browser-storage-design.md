---
codd:
  node_id: design:matrix-mvp-v2-browser-storage
  type: design
  status: draft
  depends_on:
    - id: req:matrix-mvp-v2-browser-storage
      relation: depends_on
      semantic: product
    - id: design:browser-only-matrix-runtime-storage-adr
      relation: depends_on
      semantic: decision
---

# Matrix MVP v2 Browser Storage Design

## External Design（外部設計）

v2では、React Matrix UI はブラウザSPAとして動作する。ユーザーは
`task frontend:dev` で起動したVite development server、または `pnpm build` で
生成した静的bundleをブラウザで開いて利用する。

起動時にUIはbrowser storageからtask一覧を読み込む。storageが空なら空の
Matrixを表示し、storageが壊れている場合はstorage errorを表示する。
Tauri runtime、desktop app shell、SQLite databaseは起動条件にしない。

## Internal Design（内部設計）

frontend は次の境界を持つ。

- `src/contracts/task.ts`: task、area、status、repository入出力の共有contract。
- `src/domain/taskRules.ts`: area順、title validation、status変換、表示可否などのdomain rules。
- `src/ports/taskRepository.ts`: UIとstorage adapterを分離するrepository port。
- `src/adapters/browserTaskRepository.ts`: browser storage を使う本番adapter。
- `src/ui/*`: React component、presentation、dnd-kit interaction。

`browserTaskRepository` は `siftq.tasks.v1` key に `{ version, tasks }` を保存する。
`version = 1` のみを受け入れ、予期しないshapeや壊れたJSONは `STORAGE` errorにする。

mutationは repository operation 内でtask配列を読み込み、domain ruleを適用し、
areaごとの `order` を正規化してから保存する。UIはmutation後に `listTasks` を
再実行し、storage上の状態を表示へ反映する。

IDはbrowser側で `crypto.randomUUID()` を優先し、利用できない場合は時刻と乱数を
使うfallbackを使う。ID形式を外部contractにはしない。

Done / Skipped は #59 では既存v1挙動どおり `areaId` も `done` / `skipped` に
変更する。terminal task はstorageに保持するが、Matrix通常表示からは除外する。

## Test Viewpoints（テスト観点）

- browser repository tests:
  - create / list / move / reorder / update
  - title trim と validation
  - areaごとの order 正規化
  - Done / Skipped 遷移とstorage保持
  - terminal taskをmatrix areaへ戻せないこと
  - corrupt storage error
- UI tests:
  - area表示、作成、title更新、移動、並び替え
  - Done / Skipped task が通常表示から消えること
  - browser reload相当の再mountで task title、area、status、order が復元されること
- DnD tests:
  - drop id解決、invalid drop、drag移動制限

## ADR Application（ADR 適用）

このdesignでは `ADR 0018` を適用し、#59 のruntime/storage targetを
browser-onlyへ変更する。`ADR 0003`、`ADR 0016`、`ADR 0017` のTauri / Rust /
SQLite方針は、#59 の現行スコープでは superseded として扱う。

## Open Questions（未決事項）

- 複数端末同期、公開URL、GitHub連携、CLI、IndexedDB / OPFS への移行は後続issueで扱う。
