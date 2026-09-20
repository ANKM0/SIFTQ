import { err, ok } from "../task";
import type { RepositoryError } from "./task-repository";
import type { Result, Task, TaskVersionInput } from "../task";

export function validateBulkTasks(
  inputs: readonly TaskVersionInput[],
  getTask: (id: string) => Task | undefined,
): Result<Task[], RepositoryError> {
  const ordered: Task[] = [];
  for (const input of inputs) {
    const task = getTask(input.id);
    if (!task) return err({ code: "NOT_FOUND" });
    if (task.version !== input.version) return err({ code: "CONFLICT" });
    ordered.push(task);
  }
  return ok(ordered);
}
