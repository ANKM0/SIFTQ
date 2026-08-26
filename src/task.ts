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
};

export function createTask(_input: CreateTaskInput): Result<Task, DomainError> {
  throw new Error("not implemented");
}

export function changeTaskStatus(_task: Task, _status: TaskStatus): Result<Task, DomainError> {
  throw new Error("not implemented");
}

export function changeTaskArea(_task: Task, _area: TaskArea): Result<Task, DomainError> {
  throw new Error("not implemented");
}

export function sortForMatrix(_tasks: readonly Task[]): Task[] {
  throw new Error("not implemented");
}

export function moveTask(
  _tasks: readonly Task[],
  _id: string,
  _area: TaskArea,
  _order: number,
): Task[] {
  throw new Error("not implemented");
}
