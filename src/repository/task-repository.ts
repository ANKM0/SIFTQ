import type { DomainError, Result, Task, TaskStatus, TaskVersionInput } from "../task";

export type RepositoryError = DomainError;

export interface TaskRepository {
  list(): Promise<Result<Task[], RepositoryError>>;
  find(id: string, owner_id: string): Promise<Result<Task | undefined, RepositoryError>>;
  insert(task: Task): Promise<Result<Task, RepositoryError>>;
  update(task: Task): Promise<Result<Task, RepositoryError>>;
  remove(id: string, owner_id: string, version: number): Promise<Result<null, RepositoryError>>;
  bulkUpdateStatus(
    inputs: readonly TaskVersionInput[],
    status: TaskStatus,
  ): Promise<Result<Task[], RepositoryError>>;
  bulkRemove(inputs: readonly TaskVersionInput[]): Promise<Result<null, RepositoryError>>;
  move(tasks: readonly Task[]): Promise<Result<Task[], RepositoryError>>;
}
