// Browser storage contract for the Matrix MVP. Keep this file independent from
// React so UI, storage adapters, and future sync adapters share the same shape.
export const TASK_TITLE_MAX_LENGTH = 256;

export type MatrixAreaId = "do" | "schedule" | "delegate" | "eliminate";
export type TerminalAreaId = "done" | "skipped";
export type AreaId = MatrixAreaId | TerminalAreaId;

export type TaskId = string;
export type TaskStatus = "active" | "done" | "skipped";

export type Task = {
  readonly id: TaskId;
  readonly title: string;
  readonly description: string;
  readonly areaId: AreaId;
  readonly status: TaskStatus;
  readonly order: number;
  readonly createdAt: string;
  readonly updatedAt: string;
  readonly listOrder: number;
};
