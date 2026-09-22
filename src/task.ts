export const TASK_STATUSES = ["do", "done", "skip"] as const;
export type TaskStatus = (typeof TASK_STATUSES)[number];

export const TASK_AREAS = [1, 2, 3, 4] as const;
export type TaskArea = (typeof TASK_AREAS)[number];

export const TASK_TITLE_MAX_CODE_POINTS = 256;
export const TASK_DESCRIPTION_MAX_CODE_POINTS = 16_384;

export type Task = {
  id: string;
  owner_id: string;
  title: string;
  description: string;
  status: TaskStatus;
  working: boolean;
  area: TaskArea;
  order: number;
  version: number;
  created_at: string;
  updated_at: string;
};

export type DomainErrorCode =
  | "INVALID_TITLE"
  | "INVALID_DESCRIPTION"
  | "INVALID_STATUS"
  | "INVALID_AREA"
  | "INVALID_WORKING"
  | "INVALID_ORDER"
  | "INVALID_BULK_INPUT"
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

export type TaskVersionInput = {
  id: string;
  version: number;
};

export const TASK_BULK_MAX_ITEMS = 50;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function parseTaskVersionInputs(value: unknown): Result<TaskVersionInput[], DomainError> {
  if (!Array.isArray(value) || value.length === 0 || value.length > TASK_BULK_MAX_ITEMS) {
    return err({ code: "INVALID_BULK_INPUT" });
  }

  const ids = new Set<string>();
  const inputs: TaskVersionInput[] = [];
  for (const item of value) {
    if (!isRecord(item)) return err({ code: "INVALID_BULK_INPUT" });
    const id = item["id"];
    const version = item["version"];
    if (
      typeof id !== "string" ||
      id.length === 0 ||
      ids.has(id) ||
      typeof version !== "number" ||
      !Number.isSafeInteger(version) ||
      version < 1
    ) {
      return err({ code: "INVALID_BULK_INPUT" });
    }
    ids.add(id);
    inputs.push({ id, version });
  }
  return ok(inputs);
}

export function changeTaskStatuses(
  tasks: readonly Task[],
  status: TaskStatus,
  updatedAt?: string,
): Result<Task[], DomainError> {
  const updated: Task[] = [];
  for (const task of tasks) {
    const changed = changeTaskStatus(task, status);
    if (!changed.ok) return err(changed.error);
    const next = { ...changed.value, version: task.version + 1 };
    updated.push(updatedAt === undefined ? next : { ...next, updated_at: updatedAt });
  }
  return ok(updated);
}

export function is_working(task: Task): boolean {
  return task.working;
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

export function descriptionCodePointLength(description: string): number {
  return Array.from(description).length;
}

export function isTaskDescriptionValid(description: string): boolean {
  return descriptionCodePointLength(description) <= TASK_DESCRIPTION_MAX_CODE_POINTS;
}

export type CreateTaskInput = {
  id: string;
  owner_id: string;
  title: string;
  description: string;
  status?: TaskStatus;
  area?: TaskArea;
  created_at: string;
  updated_at: string;
};

export function createTask(input: CreateTaskInput): Result<Task, DomainError> {
  if (!isTaskTitleValid(input.title)) {
    return err({ code: "INVALID_TITLE" });
  }
  if (!isTaskDescriptionValid(input.description)) {
    return err({ code: "INVALID_DESCRIPTION" });
  }

  return ok({
    id: input.id,
    owner_id: input.owner_id,
    title: input.title,
    description: input.description,
    status: input.status ?? "do",
    working: false,
    area: input.area ?? 1,
    order: 1,
    version: 1,
    created_at: input.created_at,
    updated_at: input.updated_at,
  });
}

export function changeTaskStatus(task: Task, status: TaskStatus): Result<Task, DomainError> {
  return ok({ ...task, status });
}

export function changeTaskArea(task: Task, area: TaskArea): Result<Task, DomainError> {
  return ok({ ...task, area });
}

export function changeTaskWorking(task: Task, working: boolean): Result<Task, DomainError> {
  return ok({ ...task, working });
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
