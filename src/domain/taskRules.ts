import {
  TASK_TITLE_MAX_LENGTH,
  type AreaId,
  type MatrixAreaId,
  type Task,
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
