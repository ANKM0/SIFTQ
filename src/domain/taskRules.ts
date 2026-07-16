import {
  TASK_TITLE_MAX_LENGTH,
  type AreaId,
  type MatrixAreaId,
  type Task,
  type TaskId,
  type TaskStatus
} from "../contracts/task";

export const LEGACY_TERMINAL_AREA_FALLBACK = "do" as const satisfies MatrixAreaId;

export const MATRIX_AREA_IDS = [
  "do",
  "schedule",
  "delegate",
  "eliminate"
] as const satisfies readonly MatrixAreaId[];

export const TERMINAL_AREA_IDS = [
  "skipped",
  "done"
] as const satisfies readonly Exclude<AreaId, MatrixAreaId>[];

export const AREA_ORDER = [
  ...MATRIX_AREA_IDS,
  ...TERMINAL_AREA_IDS
] as const satisfies readonly AreaId[];

export function isAreaId(areaId: string): areaId is AreaId {
  return AREA_ORDER.some((candidate) => candidate === areaId);
}

export function isMatrixArea(areaId: AreaId): areaId is MatrixAreaId {
  return MATRIX_AREA_IDS.some((candidate) => candidate === areaId);
}

export function statusForArea(areaId: AreaId): TaskStatus {
  if (areaId === "done") {
    return "done";
  }

  if (areaId === "skipped") {
    return "skipped";
  }

  return "active";
}

export function isTaskVisibleInMatrix(task: Task): boolean {
  return task.status === "active" && isMatrixArea(task.areaId);
}

export function normalizeTaskAreaId(areaId: AreaId): MatrixAreaId {
  return isMatrixArea(areaId) ? areaId : LEGACY_TERMINAL_AREA_FALLBACK;
}

export function normalizeTaskTitleInput(rawTitle: string): string {
  return rawTitle.trim();
}

export function validateTaskTitleInput(rawTitle: string): string | null {
  const title = normalizeTaskTitleInput(rawTitle);

  if (Array.from(title).length === 0) {
    return "Task title must not be empty.";
  }

  if (Array.from(title).length > TASK_TITLE_MAX_LENGTH) {
    return `Title must be ${TASK_TITLE_MAX_LENGTH} characters or less.`;
  }

  return null;
}

export function compareTasksByAreaOrder(left: Task, right: Task): number {
  return (
    AREA_ORDER.indexOf(left.areaId) - AREA_ORDER.indexOf(right.areaId) ||
    left.order - right.order ||
    left.id.localeCompare(right.id)
  );
}

export function compareTasksByListOrder(left: Task, right: Task): number {
  return (
    left.listOrder - right.listOrder ||
    left.createdAt.localeCompare(right.createdAt) ||
    left.id.localeCompare(right.id)
  );
}

export function buildDeleteTaskConfirmation(task: Pick<Task, "title">): string {
  return `"${task.title}" を削除しますか?`;
}

export function buildBulkDeleteConfirmation(selectedCount: number): string {
  return `${selectedCount}件のタスクを削除しますか?`;
}

export function formatSelectedTaskCount(selectedCount: number): string {
  return `${selectedCount}件選択中`;
}

export function toggleTaskSelection(
  selectedTaskIds: readonly TaskId[],
  taskId: TaskId,
  checked: boolean
): TaskId[] {
  if (checked) {
    return selectedTaskIds.includes(taskId) ? [...selectedTaskIds] : [...selectedTaskIds, taskId];
  }

  return selectedTaskIds.filter((candidateId) => candidateId !== taskId);
}

export function pruneSelectedTaskIds(
  selectedTaskIds: readonly TaskId[],
  tasks: readonly Pick<Task, "id">[]
): TaskId[] {
  const taskIds = new Set(tasks.map((task) => task.id));

  return selectedTaskIds.filter((taskId) => taskIds.has(taskId));
}

export function deleteTasksAndNormalizeOrder(
  tasks: readonly Task[],
  deletedTaskIds: ReadonlySet<TaskId>,
  updatedAt: string
): Task[] {
  if (deletedTaskIds.size === 0) {
    return [...tasks];
  }

  const remainingTasks = tasks.filter((task) => !deletedTaskIds.has(task.id));
  const normalizedTasks = normalizeAllAreas(remainingTasks);
  const orderedTasks = [...normalizedTasks].sort(compareTasksByListOrder);

  return orderedTasks.map((task, listOrder) =>
    task.listOrder === listOrder
      ? task
      : ({ ...task, listOrder, updatedAt } satisfies Task)
  );
}

function normalizeAllAreas(tasks: readonly Task[]): Task[] {
  return AREA_ORDER.reduce(
    (normalizedTasks, areaId) => normalizeArea(normalizedTasks, areaId),
    [...tasks]
  ).sort(compareTasksByAreaOrder);
}

function normalizeArea(tasks: readonly Task[], areaId: AreaId): Task[] {
  const normalizedAreaTasks = normalizeVisibleAreaTasks(tasksInArea(tasks, areaId));

  return replaceArea(tasks, areaId, normalizedAreaTasks).sort(compareTasksByAreaOrder);
}

function normalizeVisibleAreaTasks(tasks: readonly Task[]): Task[] {
  let nextOrder = 0;

  return tasks.map((task) =>
    isTaskVisibleInMatrix(task) ? { ...task, order: nextOrder++ } : task
  );
}

function tasksInArea(tasks: readonly Task[], areaId: AreaId): Task[] {
  return [...tasks]
    .filter((task) => task.areaId === areaId)
    .sort((left, right) => left.order - right.order || left.id.localeCompare(right.id));
}

function replaceArea(
  tasks: readonly Task[],
  areaId: AreaId,
  areaTasks: readonly Task[]
): Task[] {
  return [
    ...tasks.filter((task) => task.areaId !== areaId),
    ...areaTasks
  ];
}
