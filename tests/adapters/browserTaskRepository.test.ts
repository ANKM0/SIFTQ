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
  let nextTimestamp: number;

  beforeEach(() => {
    storage = new MemoryStorage();
    nextId = 1;
    nextTimestamp = 0;
  });

  it("creates, trims, lists, and persists browser tasks", async () => {
    const repository = repositoryForTest();

    await expect(
      repository.createTask({ areaId: "do", title: "  First  " })
    ).resolves.toMatchObject({
      areaId: "do",
      createdAt: timestampAt(0),
      description: "",
      id: "task-1",
      listOrder: 0,
      order: 0,
      status: "active",
      title: "First",
      updatedAt: timestampAt(0)
    });

    await repository.createTask({ areaId: "schedule", title: "Second" });

    expect(await repository.listTasks()).toEqual([
      task({
        id: "task-1",
        title: "First",
        areaId: "do",
        order: 0,
        createdAt: timestampAt(0),
        updatedAt: timestampAt(0),
        listOrder: 0
      }),
      task({
        id: "task-2",
        title: "Second",
        areaId: "schedule",
        order: 0,
        createdAt: timestampAt(1),
        updatedAt: timestampAt(1),
        listOrder: 1
      })
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
      task({
        id: "task-1",
        title: "First",
        areaId: "schedule",
        order: 0,
        createdAt: timestampAt(0),
        updatedAt: timestampAt(4),
        listOrder: 0
      }),
      task({
        id: "task-2",
        title: "Second",
        areaId: "do",
        order: 0,
        createdAt: timestampAt(1),
        updatedAt: timestampAt(3),
        listOrder: 1
      }),
      task({
        id: "task-3",
        title: "Scheduled",
        areaId: "schedule",
        order: 1,
        createdAt: timestampAt(2),
        updatedAt: timestampAt(2),
        listOrder: 2
      })
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
        areaId: "do",
        createdAt: timestampAt(0),
        order: 0,
        status: "done",
        updatedAt: timestampAt(2),
        listOrder: 0
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

  it("migrates legacy browser tasks missing description, timestamps, and list order", async () => {
    const repository = repositoryForTest();

    storage.setItem(
      BROWSER_TASK_STORAGE_KEY,
      JSON.stringify({
        tasks: [
          { areaId: "schedule", id: "task-2", order: 0, status: "active", title: "Second" },
          { areaId: "do", id: "task-1", order: 0, status: "active", title: "First" }
        ],
        version: 1
      })
    );

    expect(await repository.listTasks()).toEqual([
      task({
        id: "task-2",
        title: "Second",
        areaId: "schedule",
        order: 0,
        createdAt: timestampAt(0),
        updatedAt: timestampAt(0),
        listOrder: 0
      }),
      task({
        id: "task-1",
        title: "First",
        areaId: "do",
        order: 0,
        createdAt: timestampAt(1),
        updatedAt: timestampAt(1),
        listOrder: 1
      })
    ]);

    expect(JSON.parse(storage.getItem(BROWSER_TASK_STORAGE_KEY) ?? "{}")).toEqual({
      tasks: [
        task({
          id: "task-1",
          title: "First",
          areaId: "do",
          order: 0,
          createdAt: timestampAt(1),
          updatedAt: timestampAt(1),
          listOrder: 1
        }),
        task({
          id: "task-2",
          title: "Second",
          areaId: "schedule",
          order: 0,
          createdAt: timestampAt(0),
          updatedAt: timestampAt(0),
          listOrder: 0
        })
      ],
      version: 1
    });
  });

  it("reorders list order independently from matrix area order", async () => {
    const repository = repositoryForTest();

    await repository.createTask({ areaId: "do", title: "First" });
    await repository.createTask({ areaId: "schedule", title: "Second" });
    await repository.createTask({ areaId: "delegate", title: "Third" });

    await repository.reorderTaskList({ taskId: "task-3", toIndex: 0 });

    expect(await repository.listTasks()).toEqual([
      task({
        id: "task-3",
        title: "Third",
        areaId: "delegate",
        order: 0,
        createdAt: timestampAt(2),
        updatedAt: timestampAt(3),
        listOrder: 0
      }),
      task({
        id: "task-1",
        title: "First",
        areaId: "do",
        order: 0,
        createdAt: timestampAt(0),
        updatedAt: timestampAt(3),
        listOrder: 1
      }),
      task({
        id: "task-2",
        title: "Second",
        areaId: "schedule",
        order: 0,
        createdAt: timestampAt(1),
        updatedAt: timestampAt(3),
        listOrder: 2
      })
    ]);
  });

  it("preserves matrix area when status changes and restores the task to that area", async () => {
    const repository = repositoryForTest();

    await repository.createTask({ areaId: "do", title: "First" });
    await repository.createTask({ areaId: "do", title: "Second" });

    await repository.updateTaskStatus({ taskId: "task-1", status: "done" });

    expect(await repository.listTasks()).toEqual([
      task({
        id: "task-1",
        title: "First",
        areaId: "do",
        order: 1,
        createdAt: timestampAt(0),
        updatedAt: timestampAt(2),
        listOrder: 0,
        status: "done"
      }),
      task({
        id: "task-2",
        title: "Second",
        areaId: "do",
        order: 0,
        createdAt: timestampAt(1),
        updatedAt: timestampAt(1),
        listOrder: 1
      })
    ]);

    await repository.updateTaskStatus({ taskId: "task-1", status: "active" });

    expect(await repository.listTasks()).toEqual([
      task({
        id: "task-1",
        title: "First",
        areaId: "do",
        order: 1,
        createdAt: timestampAt(0),
        updatedAt: timestampAt(3),
        listOrder: 0,
        status: "active"
      }),
      task({
        id: "task-2",
        title: "Second",
        areaId: "do",
        order: 0,
        createdAt: timestampAt(1),
        updatedAt: timestampAt(1),
        listOrder: 1
      })
    ]);
  });

  it("changes area only through detail updates while preserving status", async () => {
    const repository = repositoryForTest();

    await repository.createTask({ areaId: "do", title: "First" });
    await repository.updateTaskStatus({ taskId: "task-1", status: "done" });
    await repository.updateTaskDetails({
      taskId: "task-1",
      title: "First updated",
      description: "Moved while hidden",
      areaId: "delegate",
      status: "done"
    });

    expect(await repository.listTasks()).toEqual([
      task({
        id: "task-1",
        title: "First updated",
        description: "Moved while hidden",
        areaId: "delegate",
        order: 0,
        createdAt: timestampAt(0),
        updatedAt: timestampAt(2),
        listOrder: 0,
        status: "done"
      })
    ]);
  });

  function repositoryForTest() {
    return createBrowserTaskRepository(
      storage,
      () => `task-${nextId++}`,
      BROWSER_TASK_STORAGE_KEY,
      () => timestampAt(nextTimestamp++)
    );
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
  const areaId = input.areaId ?? "do";

  return {
    areaId,
    createdAt: timestampAt(0),
    description: "",
    listOrder: input.order ?? 0,
    order: 0,
    status: areaId === "done" ? "done" : areaId === "skipped" ? "skipped" : "active",
    updatedAt: timestampAt(0),
    ...input
  };
}

function timestampAt(index: number): string {
  return new Date(index).toISOString();
}
