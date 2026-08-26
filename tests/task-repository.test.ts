import { describe, expect, it } from "vite-plus/test";
import { MemoryTaskRepository } from "./helpers/memory-task-repository";
import { taskFixture } from "./helpers/task-fixture";

describe("TaskRepository contract", () => {
  it("inserts and reads a task through the in-memory double", async () => {
    const repository = new MemoryTaskRepository();
    const task = taskFixture({ id: "task-1" });

    const inserted = await repository.insert(task);
    const listed = await repository.list();

    expect(inserted.ok).toBe(true);
    expect(listed.ok).toBe(true);
    if (!inserted.ok || !listed.ok) return;
    expect(inserted.value.id).toBe("task-1");
    expect(listed.value.map((item) => item.id)).toContain("task-1");
  });
});
