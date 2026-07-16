---
codd:
  node_id: design:matrix-terminal-drop-hitbox-fix
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: product
---

# Matrix Terminal Drop Hitbox Fix Design

## External Design（外部設計）

Matrix 画面の `Done` / `Skipped` terminal side column は、desktop では見た目の全高に
対応する drop target になる。上側、中央、下側のいずれの位置に card を重ねても
同一の terminal target として扱い、hover / highlight もその terminal 側に表示する。

terminal area 上に pointer がある間は、card droppable や matrix area droppable よりも
terminal droppable を優先する。terminal drop で task は `done` または `skipped` になり、
通常の Matrix 表示からは消えるが、task の保持 `areaId` は元の matrix area のまま維持する。

mobile 幅では既存の縦積み layout を維持し、terminal area の操作可能性を退化させない。

## Internal Design（内部設計）

### Current Collision Path Inspection

現状の Matrix 画面では、collision ranking を明示的に差し替えていない。
`src/ui/App.tsx` の Matrix 用 `DndContext` は `collisionDetection` prop を渡しておらず、
`event.over` の候補順位は dnd-kit の既定解決に委ねられている。

droppable 登録は次の構造になっている。

- `StatusDropArea` は `useDroppable({ id: areaDropId(areaId) })` で
  `area:skipped` / `area:done` を登録する。
- `AreaPanel` も同じく `useDroppable({ id: areaDropId(areaId) })` で
  `area:do` などの matrix area を登録する。
- `TaskCard` は `useDroppable({ id: taskDropId(task.id) })` で card 単位 droppable を
  登録する。

つまり `Skipped` / `Done` は専用の collision lane や priority class を持たず、
matrix area と同じ `area:*` namespace の droppable として登録されている。

`src/ui/dragDrop.ts` の `resolveTaskDropOperation()` は、dnd-kit が返した `over.id`
を受け取った後で `area:*` を `task:*` より先に解釈する。しかしこれは
`event.over` が terminal droppable に解決済みであることを前提としており、
terminal と matrix area のどちらを優先するか自体はここでは制御していない。

今回の fix では、この「terminal と matrix area の優先順位が DnD provider 側で未定義」
という状態を解消する。

collision 判定は `src/ui/dragDrop.ts` もしくは同等の resolver で行い、terminal droppable を
matrix board / card droppable より高い優先順位で評価する。

- terminal の DOM rect が pointer を含む場合は、terminal target を即時採用する。
- terminal rect に入っていない場合だけ、従来の matrix area / card collision にフォールバックする。
- matrix area 間 move / reorder の判定は、terminal rect の外では従来どおり維持する。
- task list page は別 resolver を使い、今回の優先順位変更の影響を受けない。

terminal 側の hit area は wireframe の full-height side column と一致させる。見た目上の
header / label / padding による隙間が collision の死角にならないよう、drop zone は side column
全体を包含する単一の droppable node として扱う。

## Test Viewpoints（テスト観点）

- collision helper tests:
  - Skipped / Done の terminal rect 内の上・中・下を同じ terminal target に解決する。
  - terminal rect 内では card / matrix area より terminal target が優先される。
  - terminal rect 外では従来の matrix area / card 解決を維持する。
- UI / DnD tests:
  - desktop で terminal side column 上側、中央、下側のいずれでも highlight が出る。
  - desktop で terminal drop 後に task が `done` / `skipped` になり、Matrix 通常表示から消える。
  - matrix area 間 move / reorder の既存挙動が変わらない。
  - task list page の drag/drop が変わらない。
- manual confirmation:
  - desktop で Skipped / Done の side column 全体と droppable node の矩形が一致している。
  - mobile 幅で縦積み layout と terminal 操作が破綻しない。

## ADR Application（ADR 適用）

新しい ADR は作成しない。今回の修正は既存の Matrix UI / drag-and-drop boundary の
内部実装調整であり、runtime、storage backend、toolchain、repository workflow の durable
decision を変更しない。

## Open Questions（未決事項）

- なし。
