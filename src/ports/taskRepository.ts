import {
  type AreaId,
  type MatrixAreaId,
  type Task,
  type TaskId
} from "../contracts/task";

export type CreateTaskInput = {
  readonly title: string;
  readonly areaId: MatrixAreaId;
};

export type MoveTaskInput = {
  readonly taskId: TaskId;
  readonly toAreaId: AreaId;
  readonly insertAt?: number;
};

export type ReorderTaskInput = {
  readonly taskId: TaskId;
  readonly toIndex: number;
};

export type UpdateTaskTitleInput = {
  readonly taskId: TaskId;
  readonly title: string;
};

export type TaskRepository = {
  createTask(input: CreateTaskInput): Promise<Task>;
  listTasks(): Promise<Task[]>;
  moveTask(input: MoveTaskInput): Promise<Task>;
  reorderTask(input: ReorderTaskInput): Promise<Task>;
  updateTaskTitle(input: UpdateTaskTitleInput): Promise<Task>;
};
