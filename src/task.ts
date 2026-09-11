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
  working: boolean;
  area: TaskArea;
  order: number;
  version: number;
  created_at: string;
  updated_at: string;
};

export type TaskFilter = (task: Task) => boolean;

export type DomainErrorCode =
  | "INVALID_TITLE"
  | "INVALID_STATUS"
  | "INVALID_AREA"
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

export type TaskListQuery = {
  status: TaskStatus;
  workingOnly: boolean;
};

export function parseTaskListQuery(value: unknown): TaskListQuery | null {
  if (typeof value !== "string" || value.trim() === "") return null;

  let status: TaskStatus | undefined;
  let workingOnly = false;
  for (const token of value.trim().split(/\s+/)) {
    if (token.startsWith("is:")) {
      const candidate = token.slice(3);
      if (!isTaskStatus(candidate) || status !== undefined) return null;
      status = candidate;
      continue;
    }
    if (token === "label:working" && !workingOnly) {
      workingOnly = true;
      continue;
    }
    return null;
  }

  return status === undefined ? null : { status, workingOnly };
}

export function is_do(task: Task): boolean {
  return task.status === "do";
}

export function is_done(task: Task): boolean {
  return task.status === "done";
}

export function is_skip(task: Task): boolean {
  return task.status === "skip";
}

export function is_working(task: Task): boolean {
  return task.working;
}

export const TASK_STATUS_FILTERS: Record<TaskStatus, TaskFilter> = {
  do: is_do,
  done: is_done,
  skip: is_skip,
};

export function filterTasks(tasks: readonly Task[], filters: readonly TaskFilter[]): Task[] {
  return tasks.filter((task) => filters.every((filter) => filter(task)));
}

export const TASK_LIST_PAGE_SIZE = 25;

export type PageNavItem = number | "ellipsis";

export function parsePageParam(value: unknown): number | null {
  if (typeof value !== "string" || value === "") return null;
  if (!/^\d+$/.test(value)) return null;
  const page = Number(value);
  if (!Number.isSafeInteger(page) || page < 1) return null;
  return page;
}

export function paginateTasks(
  tasks: readonly Task[],
  page: number,
  pageSize: number = TASK_LIST_PAGE_SIZE,
): { pageTasks: Task[]; currentPage: number; totalPages: number } {
  const totalPages = Math.max(1, Math.ceil(tasks.length / pageSize));
  const currentPage = Math.min(Math.max(page, 1), totalPages);
  const start = (currentPage - 1) * pageSize;
  return { pageTasks: tasks.slice(start, start + pageSize), currentPage, totalPages };
}

export function pageNavItems(currentPage: number, totalPages: number): PageNavItem[] {
  const pages = new Set([1, totalPages, currentPage - 1, currentPage, currentPage + 1]);
  const sorted = [...pages].filter((page) => page >= 1 && page <= totalPages).sort((a, b) => a - b);
  const items: PageNavItem[] = [];
  sorted.forEach((page, index) => {
    const previous = sorted[index - 1];
    if (index > 0 && previous !== undefined && page - previous > 1) items.push("ellipsis");
    items.push(page);
  });
  return items;
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
    working: false,
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

export function changeTaskWorking(task: Task, working: boolean): Result<Task, DomainError> {
  return ok({ ...task, working });
}

export function sortForMatrix(tasks: readonly Task[]): Task[] {
  return tasks
    .filter((task) => task.status === "do")
    .sort((left, right) => left.area - right.area || left.order - right.order);
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
