import {
  TASK_TITLE_MAX_LENGTH,
  type AreaId,
  type MatrixAreaId,
  type Task,
  type TerminalAreaId
} from "../contracts/task";

export type AreaRole = AreaId;
export type AreaKind = "matrix" | "terminal";

export type MatrixArea = {
  readonly id: MatrixAreaId;
  readonly label: string;
  readonly kind: "matrix";
  readonly role: MatrixAreaId;
};

export type TerminalArea = {
  readonly id: TerminalAreaId;
  readonly label: string;
  readonly kind: "terminal";
  readonly role: TerminalAreaId;
};

export type Area = MatrixArea | TerminalArea;

export const MATRIX_AREAS = [
  { id: "do", label: "Do", kind: "matrix", role: "do" },
  { id: "schedule", label: "Schedule", kind: "matrix", role: "schedule" },
  { id: "delegate", label: "Delegate", kind: "matrix", role: "delegate" },
  { id: "eliminate", label: "Eliminate", kind: "matrix", role: "eliminate" }
] as const satisfies readonly MatrixArea[];

export const TERMINAL_AREAS = [
  { id: "skipped", label: "Skipped", kind: "terminal", role: "skipped" },
  { id: "done", label: "Done", kind: "terminal", role: "done" }
] as const satisfies readonly TerminalArea[];

export const INITIAL_AREAS = [
  ...MATRIX_AREAS,
  ...TERMINAL_AREAS
] as const satisfies readonly Area[];

export function findArea(areaId: AreaId): Area {
  const area = INITIAL_AREAS.find((candidate) => candidate.id === areaId);

  if (area === undefined) {
    throw new Error(`Unknown area: ${areaId}`);
  }

  return area;
}

export function isMatrixArea(areaId: AreaId): areaId is MatrixAreaId {
  return findArea(areaId).kind === "matrix";
}

export function isTaskVisibleInMatrix(task: Task): boolean {
  return task.status === "active" && isMatrixArea(task.areaId);
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

export function tasksForArea(
  tasks: readonly Task[],
  areaId: MatrixAreaId
): Task[] {
  return tasks
    .filter((task) => task.areaId === areaId && isTaskVisibleInMatrix(task))
    .sort((left, right) => left.order - right.order);
}
