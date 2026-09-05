import { beforeEach, describe, expect, it } from "vite-plus/test";
import type { Task } from "../../src/task";
import { taskFixture } from "../helpers/task-fixture";
import { MemoryTaskRepository } from "../helpers/memory-task-repository";

let repo: MemoryTaskRepository;

beforeEach(() => {
  repo = new MemoryTaskRepository();
});

describe("repository contract", () => {
  it("inserts and lists tasks", async () => {
    const task = taskFixture({ id: "task-1" });

    const inserted = await repo.insert(task);
    const listed = await repo.list();

    expect(inserted.ok).toBe(true);
    expect(listed.ok).toBe(true);
    if (!inserted.ok || !listed.ok) return;
    expect(inserted.value).toEqual(task);
    expect(listed.value.map((item) => item.id)).toContain("task-1");
  });

  it("finds a task or returns undefined", async () => {
    await repo.insert(taskFixture({ id: "task-1" }));

    const found = await repo.find("task-1", "owner-1");
    const missing = await repo.find("missing", "owner-1");

    expect(found.ok).toBe(true);
    expect(missing.ok).toBe(true);
    if (!found.ok || !missing.ok) return;
    expect(found.value?.id).toBe("task-1");
    expect(missing.value).toBeUndefined();
  });

  it("updates with optimistic version locking", async () => {
    await repo.insert(taskFixture({ id: "task-1", version: 1 }));

    const updated = await repo.update(taskFixture({ id: "task-1", title: "updated", version: 1 }));
    const stale = await repo.update(taskFixture({ id: "task-1", title: "stale", version: 1 }));

    expect(updated.ok).toBe(true);
    expect(stale.ok).toBe(false);
    if (!updated.ok) return;
    expect(updated.value.version).toBe(2);
    if (!stale.ok) {
      expect(stale.error.code).toBe("CONFLICT");
    }
  });

  it("removes with optimistic version locking", async () => {
    await repo.insert(taskFixture({ id: "task-1", version: 1 }));

    const removed = await repo.remove("task-1", "owner-1", 1);
    const found = await repo.find("task-1", "owner-1");

    expect(removed).toEqual({ ok: true, value: null });
    expect(found).toEqual({ ok: true, value: undefined });
  });

  it("rejects removing with a stale version", async () => {
    await repo.insert(taskFixture({ id: "task-1", version: 2 }));

    const removed = await repo.remove("task-1", "owner-1", 1);

    expect(removed).toEqual({ ok: false, error: { code: "CONFLICT" } });
  });

  it("moves tasks atomically with version increments", async () => {
    await repo.insert(taskFixture({ id: "task-1", version: 1 }));
    await repo.insert(taskFixture({ id: "task-2", version: 1 }));

    const moved = await repo.move([
      taskFixture({ id: "task-1", area: 2, order: 0, version: 1 }),
      taskFixture({ id: "task-2", area: 2, order: 1, version: 1 }),
    ]);

    expect(moved.ok).toBe(true);
    if (!moved.ok) return;
    expect(moved.value.map((task: Task) => task.version)).toEqual([2, 2]);
  });
});
