import { describe, expect, it } from "vite-plus/test";
import { MemoryTaskRepository } from "../src/preview/MemoryTaskRepository";
import { PREVIEW_TASKS } from "../src/preview/tasks";
import type { Task } from "../src/task";

function firstPreviewTask(): Task {
  const task = PREVIEW_TASKS.at(0);
  if (!task) throw new Error("The preview scenario must include a task.");
  return task;
}

describe("MemoryTaskRepository", () => {
  it("stores updates with an incremented version", async () => {
    const repository = new MemoryTaskRepository(PREVIEW_TASKS);
    const task = firstPreviewTask();

    const result = await repository.update({ ...task, title: "更新済み" });

    expect(result).toEqual({ ok: true, value: { ...task, title: "更新済み", version: 2 } });
    expect(await repository.find(task.id, task.owner_id)).toEqual({
      ok: true,
      value: { ...task, title: "更新済み", version: 2 },
    });
  });

  it("rejects a stale update", async () => {
    const repository = new MemoryTaskRepository(PREVIEW_TASKS);
    const task = firstPreviewTask();

    const result = await repository.update({ ...task, version: 2 });

    expect(result).toEqual({ ok: false, error: { code: "CONFLICT" } });
  });

  it("removes a task with the current version", async () => {
    const repository = new MemoryTaskRepository(PREVIEW_TASKS);
    const task = firstPreviewTask();

    const result = await repository.remove(task.id, task.owner_id, task.version);

    expect(result).toEqual({ ok: true, value: null });
    expect(await repository.find(task.id, task.owner_id)).toEqual({ ok: true, value: undefined });
  });

  it("rejects removing a task with a stale version", async () => {
    const repository = new MemoryTaskRepository(PREVIEW_TASKS);
    const task = firstPreviewTask();

    const result = await repository.remove(task.id, task.owner_id, task.version + 1);

    expect(result).toEqual({ ok: false, error: { code: "CONFLICT" } });
  });
});
