export type TaskStatus = "do" | "done" | "skip";
export type TaskArea = 1 | 2 | 3 | 4;

export interface Task {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  area: TaskArea;
  order: number;
}

export const TASK_STATUSES: readonly TaskStatus[] = ["do", "done", "skip"];
export const TASK_AREAS: readonly TaskArea[] = [1, 2, 3, 4];

export function isTaskStatus(value: unknown): value is TaskStatus {
  return value === "do" || value === "done" || value === "skip";
}

export function isTaskArea(value: unknown): value is TaskArea {
  return value === 1 || value === 2 || value === 3 || value === 4;
}

export function createTask(input: {
  title: string;
  description?: string;
}): Task {
  return {
    id: crypto.randomUUID(),
    title: input.title,
    description: input.description ?? "",
    status: "do",
    area: 1,
    order: 0,
  };
}

export function updateTask(
  task: Task,
  input: { title: string; description: string }
): Task {
  return { ...task, title: input.title, description: input.description };
}

export function changeTaskStatus(task: Task, status: TaskStatus): Task {
  return { ...task, status };
}

export function changeTaskArea(task: Task, area: TaskArea): Task {
  return { ...task, area };
}

export function sortForMatrix(tasks: readonly Task[]): Task[] {
  return tasks
    .filter((task) => task.status === "do")
    .sort((a, b) => a.area - b.area || a.order - b.order);
}

export function seedTasks(): Task[] {
  return [
    {
      id: "seed-1",
      title: "Set up D1 database",
      description: "Create the schema and bindings.",
      status: "do",
      area: 1,
      order: 0,
    },
    {
      id: "seed-2",
      title: "Adopt version optimistic locking",
      description: "Add version column and conflict handling.",
      status: "do",
      area: 1,
      order: 1,
    },
    {
      id: "seed-3",
      title: "Move Matrix to HTMX partial updates",
      description: "Replace React SPA with Hono JSX + HTMX.",
      status: "do",
      area: 2,
      order: 0,
    },
    {
      id: "seed-4",
      title: "Add SortableJS drag and drop",
      description: "Reorder the Matrix with SortableJS.",
      status: "do",
      area: 3,
      order: 0,
    },
    {
      id: "seed-5",
      title: "Review ADR 0007",
      description: "Confirm D1 as the system of record.",
      status: "done",
      area: 4,
      order: 0,
    },
  ];
}
