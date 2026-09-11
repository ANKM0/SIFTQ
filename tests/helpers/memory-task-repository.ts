import { changeTaskStatus, err, ok } from "../../src/task";
import type { Result, Task, TaskStatus, TaskVersionInput } from "../../src/task";
import { validateBulkTasks } from "../../src/task-repository";
import type { RepositoryError, TaskRepository } from "../../src/task-repository";

export class MemoryTaskRepository implements TaskRepository {
  private readonly tasks = new Map<string, Task>();

  async list(): Promise<Result<Task[], RepositoryError>> {
    return ok<Task[], RepositoryError>([...this.tasks.values()]);
  }

  async find(id: string, _owner_id: string): Promise<Result<Task | undefined, RepositoryError>> {
    return ok<Task | undefined, RepositoryError>(this.tasks.get(id));
  }

  async insert(task: Task): Promise<Result<Task, RepositoryError>> {
    this.tasks.set(task.id, task);
    return ok<Task, RepositoryError>(task);
  }

  async update(task: Task): Promise<Result<Task, RepositoryError>> {
    const current = this.tasks.get(task.id);
    if (!current) {
      return err<Task, RepositoryError>({ code: "NOT_FOUND" });
    }
    if (current.version !== task.version) {
      return err<Task, RepositoryError>({ code: "CONFLICT" });
    }

    const updated: Task = { ...task, version: task.version + 1 };
    this.tasks.set(updated.id, updated);
    return ok<Task, RepositoryError>(updated);
  }

  async remove(id: string, _owner_id: string, version: number): Promise<Result<null, RepositoryError>> {
    const current = this.tasks.get(id);
    if (!current) {
      return err<null, RepositoryError>({ code: "NOT_FOUND" });
    }
    if (current.version !== version) return err<null, RepositoryError>({ code: "CONFLICT" });

    this.tasks.delete(id);
    return ok<null, RepositoryError>(null);
  }

  async bulkUpdateStatus(
    inputs: readonly TaskVersionInput[],
    status: TaskStatus,
  ): Promise<Result<Task[], RepositoryError>> {
    const current = validateBulkTasks(inputs, (id) => this.tasks.get(id));
    if (!current.ok) return current;
    const updated: Task[] = [];
    for (const task of current.value) {
      const changed = changeTaskStatus(task, status);
      if (!changed.ok) return err(changed.error);
      updated.push({ ...changed.value, version: task.version + 1 });
    }
    updated.forEach((task) => this.tasks.set(task.id, task));
    return ok(updated);
  }

  async bulkRemove(inputs: readonly TaskVersionInput[]): Promise<Result<null, RepositoryError>> {
    const current = validateBulkTasks(inputs, (id) => this.tasks.get(id));
    if (!current.ok) return current;
    current.value.forEach((task) => this.tasks.delete(task.id));
    return ok(null);
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
