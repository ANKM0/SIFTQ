export const TASK_STATUSES = ["do", "done", "skip"] as const;
export type TaskStatus = (typeof TASK_STATUSES)[number];

export const TASK_AREAS = [1, 2, 3, 4] as const;
export type TaskArea = (typeof TASK_AREAS)[number];

export const TASK_TITLE_MAX_CODE_POINTS = 256;

export type Task = {
  id: string;
  owner_id: string;
  title: string;
  description: string;
  status: TaskStatus;
  area: TaskArea;
  order: number;
  version: number;
  created_at: string;
  updated_at: string;
};

export type DomainErrorCode =
  | "INVALID_TITLE"
  | "INVALID_STATUS"
  | "INVALID_AREA"
  | "INVALID_ORDER"
  | "NOT_FOUND"
  | "CONFLICT";

export type DomainError = { code: DomainErrorCode };

export type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };

export function ok<T, E>(value: T): Result<T, E> {
  return { ok: true, value };
}

export function err<T, E>(error: E): Result<T, E> {
  return { ok: false, error };
}

export function isTaskStatus(value: unknown): value is TaskStatus {
  return typeof value === "string" && TASK_STATUSES.some((status) => status === value);
}

export function isTaskArea(value: unknown): value is TaskArea {
  return typeof value === "number" && TASK_AREAS.some((area) => area === value);
}

export function titleCodePointLength(title: string): number {
  return Array.from(title).length;
}

export function isTaskTitleValid(title: string): boolean {
  const length = titleCodePointLength(title);
  return length >= 1 && length <= TASK_TITLE_MAX_CODE_POINTS;
}

export type CreateTaskInput = {
  owner_id: string;
  title: string;
  description: string;
  status?: TaskStatus;
  area?: TaskArea;
};

export function createTask(input: CreateTaskInput): Result<Task, DomainError> {
  if (!isTaskTitleValid(input.title)) {
    return err({ code: "INVALID_TITLE" });
  }

  const now = new Date().toISOString();
  return ok({
    id: crypto.randomUUID(),
    owner_id: input.owner_id,
    title: input.title,
    description: input.description,
    status: input.status ?? "do",
    area: input.area ?? 1,
    order: 1,
    version: 1,
    created_at: now,
    updated_at: now,
  });
}

export function changeTaskStatus(task: Task, status: TaskStatus): Result<Task, DomainError> {
  return ok({ ...task, status });
}

export function changeTaskArea(task: Task, area: TaskArea): Result<Task, DomainError> {
  return ok({ ...task, area });
}

export function sortForMatrix(tasks: readonly Task[], sortKey?: unknown): Task[] {
  const key = isMatrixSortKey(sortKey) ? sortKey : "order";
  return tasks
    .filter((task) => task.status === "do")
    .sort(
      (left, right) =>
        left.area - right.area ||
        compareBySortKey(left, right, key) ||
        left.order - right.order,
    );
}

export const MATRIX_SORT_KEYS = ["order", "title", "created_at", "updated_at"] as const;
export type MatrixSortKey = (typeof MATRIX_SORT_KEYS)[number];

export function isMatrixSortKey(value: unknown): value is MatrixSortKey {
  return typeof value === "string" && MATRIX_SORT_KEYS.some((key) => key === value);
}

function compareBySortKey(left: Task, right: Task, key: MatrixSortKey): number {
  switch (key) {
    case "title":
      return left.title.localeCompare(right.title);
    case "created_at":
      return compareIsoTime(left.created_at, right.created_at);
    case "updated_at":
      return compareIsoTime(left.updated_at, right.updated_at);
    case "order":
    default:
      return left.order - right.order;
  }
}

function compareIsoTime(left: string, right: string): number {
  if (left < right) return -1;
  if (left > right) return 1;
  return 0;
}

export function moveTask(
  tasks: readonly Task[],
  id: string,
  area: TaskArea,
  order: number,
): Result<Task[], DomainError> {
  const target = tasks.find((task) => task.id === id);
  if (!target) {
    return err({ code: "NOT_FOUND" });
  }
  if (!Number.isInteger(order) || order < 0) {
    return err({ code: "INVALID_ORDER" });
  }

  const sourceArea = target.area;
  const rest = tasks.filter((task) => task.id !== id).map((task) => ({ ...task }));
  const destination = rest
    .filter((task) => task.area === area)
    .sort((left, right) => left.order - right.order);
  const clampedOrder = Math.min(order, destination.length);

  for (const task of destination) {
    if (task.order >= clampedOrder) {
      task.order += 1;
    }
  }

  const moved = { ...target, area, order: clampedOrder };
  const normalizedDestination = [...destination, moved]
    .sort((left, right) => left.order - right.order)
    .map((task, index) => ({ ...task, order: index }));

  const remaining = rest.filter((task) => task.area !== area);
  if (sourceArea === area) {
    return ok([...remaining, ...normalizedDestination]);
  }

  const normalizedSource = remaining
    .filter((task) => task.area === sourceArea)
    .sort((left, right) => left.order - right.order)
    .map((task, index) => ({ ...task, order: index }));
  const untouched = remaining.filter((task) => task.area !== sourceArea);

  return ok([...untouched, ...normalizedSource, ...normalizedDestination]);
}
