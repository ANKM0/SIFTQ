import { isTaskStatus } from "./task";
import type { Task, TaskStatus } from "./task";

export type TaskFilter = (task: Task) => boolean;

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

export function sortForMatrix(tasks: readonly Task[]): Task[] {
  return tasks
    .filter((task) => task.status === "do")
    .sort((left, right) => left.area - right.area || left.order - right.order);
}
