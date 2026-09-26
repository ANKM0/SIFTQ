import type { Task, TaskArea, TaskStatus } from "../task";

const SEED_TASKS: readonly Task[] = [
  {
    id: "preview-task",
    owner_id: "local",
    title: "Matrix のタスクカードを見直す",
    description: "タスクの内容を確認しやすいカード表現を検討する。",
    status: "do",
    working: true,
    area: 1,
    order: 0,
    version: 1,
    created_at: "2026-08-29T00:00:00.000Z",
    updated_at: "2026-08-29T00:00:00.000Z",
  },
  {
    id: "preview-task-2",
    owner_id: "local",
    title: "新規タスク作成の操作を確認する",
    description: "",
    status: "do",
    working: false,
    area: 2,
    order: 0,
    version: 1,
    created_at: "2026-08-29T00:00:00.000Z",
    updated_at: "2026-08-29T00:00:00.000Z",
  },
  {
    id: "preview-task-3",
    owner_id: "local",
    title: "完了したタスクの表示を確認する",
    description: "",
    status: "done",
    working: true,
    area: 3,
    order: 0,
    version: 1,
    created_at: "2026-08-29T00:00:00.000Z",
    updated_at: "2026-08-29T00:00:00.000Z",
  },
  {
    id: "preview-task-4",
    owner_id: "local",
    title: "見送ったタスクの表示を確認する",
    description: "",
    status: "skip",
    working: false,
    area: 4,
    order: 0,
    version: 1,
    created_at: "2026-08-29T00:00:00.000Z",
    updated_at: "2026-08-29T00:00:00.000Z",
  },
];

const BULK_STATUSES: readonly TaskStatus[] = ["do", "done", "skip"];
const BULK_PER_STATUS = 60;
const BULK_BASE_TIME = Date.UTC(2026, 6, 1, 0, 0, 0);

function bulkArea(index: number): TaskArea {
  switch (index % 4) {
    case 0:
      return 1;
    case 1:
      return 2;
    case 2:
      return 3;
    default:
      return 4;
  }
}

function bulkTasks(status: TaskStatus): Task[] {
  return Array.from({ length: BULK_PER_STATUS }, (_, index) => {
    const timestamp = new Date(BULK_BASE_TIME + index * 60_000).toISOString();
    return {
      id: `preview-bulk-${status}-${index + 1}`,
      owner_id: "local",
      title: `[${status}] ページング確認 ${String(index + 1).padStart(2, "0")}`,
      description: "",
      status,
      working: status === "do" && index % 2 === 0,
      area: bulkArea(index),
      order: index,
      version: 1,
      created_at: timestamp,
      updated_at: timestamp,
    };
  });
}

export const PREVIEW_TASKS: readonly Task[] = [
  ...SEED_TASKS,
  ...BULK_STATUSES.flatMap((status) => bulkTasks(status)),
];
