import { changeTaskStatuses, err, ok } from "../task";
import type { Result, Task, TaskStatus, TaskVersionInput } from "../task";
import { validateBulkTasks } from "../task-repository";
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

  async bulkUpdateStatus(
    inputs: readonly TaskVersionInput[],
    status: TaskStatus,
  ): Promise<Result<Task[], RepositoryError>> {
    return this.applyBulkStatus(validateBulkTasks(inputs, (id) => this.tasks.get(id)), status);
  }

  private applyBulkStatus(
    current: Result<Task[], RepositoryError>,
    status: TaskStatus,
  ): Result<Task[], RepositoryError> {
    if (!current.ok) return current;
    const updated = changeTaskStatuses(current.value, status);
    if (updated.ok) updated.value.forEach((task) => this.tasks.set(task.id, task));
    return updated;
  }

  async bulkRemove(inputs: readonly TaskVersionInput[]): Promise<Result<null, RepositoryError>> {
    const current = validateBulkTasks(inputs, (id) => this.tasks.get(id));
    if (current.ok) {
      for (const task of current.value) this.tasks.delete(task.id);
      return ok(null);
    }
    return err(current.error);
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
