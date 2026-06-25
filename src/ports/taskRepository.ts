import {
  type AreaId,
  type MatrixAreaId,
  type Task,
  type TaskId,
  type TaskStatus
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

export type ReorderTaskListInput = {
  readonly taskId: TaskId;
  readonly toIndex: number;
};

export type UpdateTaskTitleInput = {
  readonly taskId: TaskId;
  readonly title: string;
};

export type UpdateTaskStatusInput = {
  readonly taskId: TaskId;
  readonly status: TaskStatus;
};

export type UpdateTaskDetailsInput = {
  readonly taskId: TaskId;
  readonly title: string;
  readonly description: string;
  readonly areaId: MatrixAreaId;
  readonly status: TaskStatus;
};

export type TaskRepository = {
  createTask(input: CreateTaskInput): Promise<Task>;
  listTasks(): Promise<Task[]>;
  moveTask(input: MoveTaskInput): Promise<Task>;
  reorderTask(input: ReorderTaskInput): Promise<Task>;
  reorderTaskList(input: ReorderTaskListInput): Promise<Task>;
  updateTaskTitle(input: UpdateTaskTitleInput): Promise<Task>;
  updateTaskStatus(input: UpdateTaskStatusInput): Promise<Task>;
  updateTaskDetails(input: UpdateTaskDetailsInput): Promise<Task>;
};
