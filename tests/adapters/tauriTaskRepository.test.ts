import { describe, expect, it } from "vitest";

import {
  createTauriTaskRepository,
  getStorageHealth,
  TauriCommandError
} from "../../src/adapters/tauriTaskRepository";
import { type InvokeArgs } from "../../src/adapters/tauriInvoke";
import { type Task } from "../../src/contracts/task";

describe("tauriTaskRepository", () => {
  it("maps repository operations to Tauri commands and trims titles", async () => {
    const calls: Array<{ command: string; args?: InvokeArgs }> = [];
    const returnedTask = task({ id: "task-1", title: "First" });
    const repository = createTauriTaskRepository(
      async <T,>(command: string, args?: InvokeArgs) => {
      calls.push({ command, args });

      return returnedTask as T;
      }
    );

    await expect(
      repository.createTask({ areaId: "do", title: "  First  " })
    ).resolves.toEqual(returnedTask);
    await repository.moveTask({
      taskId: "task-1",
      toAreaId: "schedule",
      insertAt: 0
    });
    await repository.reorderTask({ taskId: "task-1", toIndex: 1 });
    await repository.updateTaskTitle({ taskId: "task-1", title: "  Revised  " });

    expect(calls).toEqual([
      {
        command: "create_task",
        args: { input: { areaId: "do", title: "First" } }
      },
      {
        command: "move_task",
        args: {
          input: { taskId: "task-1", toAreaId: "schedule", insertAt: 0 }
        }
      },
      {
        command: "reorder_task",
        args: { input: { taskId: "task-1", toIndex: 1 } }
      },
      {
        command: "update_task_title",
        args: { input: { taskId: "task-1", title: "Revised" } }
      }
    ]);
  });

  it("lists all tasks returned by the command adapter", async () => {
    const tasks = [
      task({ id: "task-1", title: "First" }),
      task({ id: "task-2", title: "Done", areaId: "done", status: "done" })
    ];
    const repository = createTauriTaskRepository(async <T,>() => tasks as T);

    await expect(repository.listTasks()).resolves.toEqual(tasks);
  });

  it("normalizes structured command errors", async () => {
    const repository = createTauriTaskRepository(async () => {
      throw { code: "VALIDATION", message: "Task title must not be empty." };
    });

    await expect(repository.listTasks()).rejects.toMatchObject({
      code: "VALIDATION",
      message: "Task title must not be empty.",
      name: "TauriCommandError"
    } satisfies Partial<TauriCommandError>);
  });

  it("checks storage health through the dedicated command", async () => {
    const calls: string[] = [];
    const health = await getStorageHealth(async <T,>(command: string) => {
      calls.push(command);

      return { ok: true } as T;
    });

    expect(health).toEqual({ ok: true });
    expect(calls).toEqual(["get_storage_health"]);
  });
});

function task(input: Partial<Task> & Pick<Task, "id" | "title">): Task {
  return {
    areaId: "do",
    order: 0,
    status: "active",
    ...input
  };
}
