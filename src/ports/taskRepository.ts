import { type AreaId, type MatrixAreaId } from "../domain/area";
import { type Task, type TaskId } from "../domain/task";

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

export type TaskRepository = {
  createTask(input: CreateTaskInput): Promise<Task>;
  listTasks(): Promise<Task[]>;
  moveTask(input: MoveTaskInput): Promise<Task>;
  reorderTask(input: ReorderTaskInput): Promise<Task>;
};
