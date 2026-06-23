import { beforeEach, describe, expect, it } from "vitest";

import {
  BROWSER_TASK_STORAGE_KEY,
  BrowserTaskRepositoryError,
  createBrowserTaskRepository
} from "../../src/adapters/browserTaskRepository";
import { type Task } from "../../src/contracts/task";

describe("browserTaskRepository", () => {
  let storage: MemoryStorage;
  let nextId: number;

  beforeEach(() => {
    storage = new MemoryStorage();
    nextId = 1;
  });

  it("creates, trims, lists, and persists browser tasks", async () => {
    const repository = repositoryForTest();

    await expect(
      repository.createTask({ areaId: "do", title: "  First  " })
    ).resolves.toMatchObject({
      areaId: "do",
      id: "task-1",
      order: 0,
      status: "active",
      title: "First"
    });

    await repository.createTask({ areaId: "schedule", title: "Second" });

    expect(await repository.listTasks()).toEqual([
      task({ id: "task-1", title: "First", areaId: "do", order: 0 }),
      task({ id: "task-2", title: "Second", areaId: "schedule", order: 0 })
    ]);

    expect(JSON.parse(storage.getItem(BROWSER_TASK_STORAGE_KEY) ?? "{}")).toEqual({
      tasks: await repository.listTasks(),
      version: 1
    });
  });

  it("reorders and moves tasks while normalizing area order", async () => {
    const repository = repositoryForTest();

    await repository.createTask({ areaId: "do", title: "First" });
    await repository.createTask({ areaId: "do", title: "Second" });
    await repository.createTask({ areaId: "schedule", title: "Scheduled" });

    await repository.reorderTask({ taskId: "task-2", toIndex: 0 });
    await repository.moveTask({ taskId: "task-1", toAreaId: "schedule", insertAt: 0 });

    expect(await repository.listTasks()).toEqual([
      task({ id: "task-2", title: "Second", areaId: "do", order: 0 }),
      task({ id: "task-1", title: "First", areaId: "schedule", order: 0 }),
      task({ id: "task-3", title: "Scheduled", areaId: "schedule", order: 1 })
    ]);
  });

  it("keeps terminal tasks in storage and hidden from matrix state", async () => {
    const repository = repositoryForTest();

    await repository.createTask({ areaId: "do", title: "Done soon" });
    await repository.moveTask({ taskId: "task-1", toAreaId: "done", insertAt: 0 });
    await repository.updateTaskTitle({ taskId: "task-1", title: "Done title" });

    expect(await repository.listTasks()).toEqual([
      task({
        id: "task-1",
        title: "Done title",
        areaId: "done",
        order: 0,
        status: "done"
      })
    ]);
    await expect(
      repository.moveTask({ taskId: "task-1", toAreaId: "do", insertAt: 0 })
    ).rejects.toMatchObject({
      code: "VALIDATION",
      name: "BrowserTaskRepositoryError"
    } satisfies Partial<BrowserTaskRepositoryError>);
  });

  it("rejects invalid titles and corrupt storage", async () => {
    const repository = repositoryForTest();

    await expect(repository.createTask({ areaId: "do", title: "   " })).rejects.toMatchObject({
      code: "VALIDATION",
      message: "Task title must not be empty."
    } satisfies Partial<BrowserTaskRepositoryError>);

    storage.setItem(BROWSER_TASK_STORAGE_KEY, "{");

    await expect(repository.listTasks()).rejects.toMatchObject({
      code: "STORAGE",
      name: "BrowserTaskRepositoryError"
    } satisfies Partial<BrowserTaskRepositoryError>);
  });

  function repositoryForTest() {
    return createBrowserTaskRepository(storage, () => `task-${nextId++}`);
  }
});

class MemoryStorage implements Pick<Storage, "getItem" | "setItem"> {
  private readonly items = new Map<string, string>();

  getItem(key: string): string | null {
    return this.items.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.items.set(key, value);
  }
}

function task(input: Partial<Task> & Pick<Task, "id" | "title">): Task {
  return {
    areaId: "do",
    order: 0,
    status: "active",
    ...input
  };
}
