import {
  type AreaId,
  type MatrixAreaId,
  type Task,
  type TerminalAreaId
} from "../contracts/task";
import { isTaskVisibleInMatrix } from "../domain/taskRules";

export {
  isMatrixArea,
  isTaskVisibleInMatrix,
  normalizeTaskTitleInput,
  validateTaskTitleInput
} from "../domain/taskRules";

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

export function tasksForArea(
  tasks: readonly Task[],
  areaId: MatrixAreaId
): Task[] {
  return tasks
    .filter((task) => task.areaId === areaId && isTaskVisibleInMatrix(task))
    .sort((left, right) => left.order - right.order);
}
