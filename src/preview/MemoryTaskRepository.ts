import { err, ok } from "../task";
import type { Result, Task } from "../task";
import type { RepositoryError, TaskRepository } from "../task-repository";

export class MemoryTaskRepository implements TaskRepository {
  private readonly tasks: Map<string, Task>;

  constructor(initialTasks: readonly Task[] = []) {
    this.tasks = new Map(initialTasks.map((task) => [task.id, task]));
  }

  async list(): Promise<Result<Task[], RepositoryError>> {
    return ok<Task[], RepositoryError>([...this.tasks.values()]);
  }

  async find(id: string, _ownerId: string): Promise<Result<Task | undefined, RepositoryError>> {
    return ok<Task | undefined, RepositoryError>(this.tasks.get(id));
  }

  async insert(task: Task): Promise<Result<Task, RepositoryError>> {
    this.tasks.set(task.id, task);
    return ok<Task, RepositoryError>(task);
  }

  async update(task: Task): Promise<Result<Task, RepositoryError>> {
    const current = this.tasks.get(task.id);
    if (!current) return err<Task, RepositoryError>({ code: "NOT_FOUND" });
    if (current.version !== task.version) return err<Task, RepositoryError>({ code: "CONFLICT" });

    const updated: Task = { ...task, version: task.version + 1 };
    this.tasks.set(updated.id, updated);
    return ok<Task, RepositoryError>(updated);
  }

  async remove(id: string, _ownerId: string, version: number): Promise<Result<null, RepositoryError>> {
    const current = this.tasks.get(id);
    if (!current) {
      return err<null, RepositoryError>({ code: "NOT_FOUND" });
    }
    if (current.version !== version) return err<null, RepositoryError>({ code: "CONFLICT" });

    this.tasks.delete(id);
    return ok<null, RepositoryError>(null);
  }

  async move(tasks: readonly Task[]): Promise<Result<Task[], RepositoryError>> {
    for (const task of tasks) {
      const current = this.tasks.get(task.id);
      if (!current || current.version !== task.version) {
        return err<Task[], RepositoryError>({ code: "CONFLICT" });
      }
    }

    const updated = tasks.map((task) => ({ ...task, version: task.version + 1 }));
    for (const task of updated) {
      this.tasks.set(task.id, task);
    }
    return ok<Task[], RepositoryError>(updated);
  }
}
