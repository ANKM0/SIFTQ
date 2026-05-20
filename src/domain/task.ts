import { type AreaId, isMatrixArea } from "./area";

export const TASK_TITLE_MAX_LENGTH = 256;

export type TaskId = string;
export type TaskStatus = "active" | "done" | "skipped";

export type Task = {
  readonly id: TaskId;
  readonly title: string;
  readonly areaId: AreaId;
  readonly status: TaskStatus;
  readonly order: number;
};

export class TaskValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TaskValidationError";
  }
}

export function normalizeTaskTitle(rawTitle: string): string {
  const title = rawTitle.trim();

  if (title.length === 0) {
    throw new TaskValidationError("Task title must not be empty.");
  }

  if (title.length > TASK_TITLE_MAX_LENGTH) {
    throw new TaskValidationError(
      `Task title must be ${TASK_TITLE_MAX_LENGTH} characters or less.`
    );
  }

  return title;
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
