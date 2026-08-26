import type { DomainError, Result, Task } from "./task";

export type RepositoryError = DomainError;

export interface TaskRepository {
  list(): Promise<Result<Task[], RepositoryError>>;
  find(id: string, owner_id: string): Promise<Result<Task | undefined, RepositoryError>>;
  insert(task: Task): Promise<Result<Task, RepositoryError>>;
  update(task: Task): Promise<Result<Task, RepositoryError>>;
  move(tasks: readonly Task[]): Promise<Result<Task[], RepositoryError>>;
}

export class D1TaskRepository implements TaskRepository {
  async list(): Promise<Result<Task[], RepositoryError>> {
    throw new Error("not implemented");
  }

  async find(_id: string, _owner_id: string): Promise<Result<Task | undefined, RepositoryError>> {
    throw new Error("not implemented");
  }

  async insert(_task: Task): Promise<Result<Task, RepositoryError>> {
    throw new Error("not implemented");
  }

  async update(_task: Task): Promise<Result<Task, RepositoryError>> {
    throw new Error("not implemented");
  }

  async move(_tasks: readonly Task[]): Promise<Result<Task[], RepositoryError>> {
    throw new Error("not implemented");
  }
}
