// MEMO: Replace these hand-written #59 contracts with generated TypeScript
// types from Rust once the command surface is stable.
export const TASK_TITLE_MAX_LENGTH = 256;

export type MatrixAreaId = "do" | "schedule" | "delegate" | "eliminate";
export type TerminalAreaId = "done" | "skipped";
export type AreaId = MatrixAreaId | TerminalAreaId;

export type TaskId = string;
export type TaskStatus = "active" | "done" | "skipped";

export type Task = {
  readonly id: TaskId;
  readonly title: string;
  readonly areaId: AreaId;
  readonly status: TaskStatus;
  readonly order: number;
};

export type TaskDto = Task;

export type CommandErrorCode =
  | "VALIDATION"
  | "NOT_FOUND"
  | "STORAGE"
  | "MIGRATION"
  | "INTERNAL";

export type CommandErrorDto = {
  readonly code: CommandErrorCode | string;
  readonly message: string;
};

export type StorageHealthDto =
  | {
      readonly ok: true;
    }
  | {
      readonly ok: false;
      readonly code: CommandErrorCode | string;
      readonly message: string;
    };

export type CreateTaskRequest = {
  readonly title: string;
  readonly areaId: MatrixAreaId;
};

export type MoveTaskRequest = {
  readonly taskId: TaskId;
  readonly toAreaId: AreaId;
  readonly insertAt?: number;
};

export type ReorderTaskRequest = {
  readonly taskId: TaskId;
  readonly toIndex: number;
};

export type UpdateTaskTitleRequest = {
  readonly taskId: TaskId;
  readonly title: string;
};
