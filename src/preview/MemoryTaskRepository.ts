import { changeTaskStatuses, err, ok } from "../task";
import type { Result, Task, TaskStatus, TaskVersionInput } from "../task";
import { validateBulkTasks } from "../repository/repository-validation";
import type { RepositoryError, TaskRepository } from "../repository/task-repository";

export function createMemoryTaskRepository(initialTasks: readonly Task[] = []): TaskRepository {
  const tasks = new Map(initialTasks.map((task) => [task.id, task]));

  async function list(): Promise<Result<Task[], RepositoryError>> {
    return ok<Task[], RepositoryError>([...tasks.values()]);
  }

  async function find(id: string, _ownerId: string): Promise<Result<Task | undefined, RepositoryError>> {
    return ok<Task | undefined, RepositoryError>(tasks.get(id));
  }

  async function insert(task: Task): Promise<Result<Task, RepositoryError>> {
    tasks.set(task.id, task);
    return ok<Task, RepositoryError>(task);
  }

  async function update(task: Task): Promise<Result<Task, RepositoryError>> {
    const current = tasks.get(task.id);
    if (!current) return err<Task, RepositoryError>({ code: "NOT_FOUND" });
    if (current.version !== task.version) return err<Task, RepositoryError>({ code: "CONFLICT" });

    const updated: Task = { ...task, version: task.version + 1 };
    tasks.set(updated.id, updated);
    return ok<Task, RepositoryError>(updated);
  }

  async function bulkUpdateStatus(
    inputs: readonly TaskVersionInput[],
    status: TaskStatus,
  ): Promise<Result<Task[], RepositoryError>> {
    return applyBulkStatus(tasks, validateBulkTasks(inputs, (id) => tasks.get(id)), status);
  }

  async function bulkRemove(inputs: readonly TaskVersionInput[]): Promise<Result<null, RepositoryError>> {
    const current = validateBulkTasks(inputs, (id) => tasks.get(id));
    if (current.ok) {
      for (const task of current.value) tasks.delete(task.id);
      return ok(null);
    }
    return err(current.error);
  }

  async function remove(id: string, _ownerId: string, version: number): Promise<Result<null, RepositoryError>> {
    const current = tasks.get(id);
    if (!current) {
      return err<null, RepositoryError>({ code: "NOT_FOUND" });
    }
    if (current.version !== version) return err<null, RepositoryError>({ code: "CONFLICT" });

    tasks.delete(id);
    return ok<null, RepositoryError>(null);
  }

  async function move(inputTasks: readonly Task[]): Promise<Result<Task[], RepositoryError>> {
    for (const task of inputTasks) {
      const current = tasks.get(task.id);
      if (!current || current.version !== task.version) {
        return err<Task[], RepositoryError>({ code: "CONFLICT" });
      }
    }

    const updated = inputTasks.map((task) => ({ ...task, version: task.version + 1 }));
    for (const task of updated) {
      tasks.set(task.id, task);
    }
    return ok<Task[], RepositoryError>(updated);
  }

  return { list, find, insert, update, remove, bulkUpdateStatus, bulkRemove, move };
}

function applyBulkStatus(
  tasks: Map<string, Task>,
  current: Result<Task[], RepositoryError>,
  status: TaskStatus,
): Result<Task[], RepositoryError> {
  if (!current.ok) return current;
  const updated = changeTaskStatuses(current.value, status);
  if (updated.ok) updated.value.forEach((task) => tasks.set(task.id, task));
  return updated;
}
