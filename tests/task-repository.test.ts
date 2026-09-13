import { describe, expect, it } from "vite-plus/test";
import type { D1Database } from "@cloudflare/workers-types";
import { createMemoryTaskRepository } from "./helpers/memory-task-repository";
import { taskFixture } from "./helpers/task-fixture";
import { createD1TaskRepository, type TaskRepository } from "../src/task-repository";

const unusedD1Database = {
  prepare() {
    throw new Error("D1 is not used by this factory contract test.");
  },
  batch() {
    throw new Error("D1 is not used by this factory contract test.");
  },
  exec() {
    throw new Error("D1 is not used by this factory contract test.");
  },
  withSession() {
    throw new Error("D1 is not used by this factory contract test.");
  },
  dump() {
    throw new Error("D1 is not used by this factory contract test.");
  },
} satisfies D1Database;

const repositoryMethods = ["bulkRemove", "bulkUpdateStatus", "find", "insert", "list", "move", "remove", "update"];

describe("TaskRepository contract", () => {
  it("inserts and reads a task through the in-memory double", async () => {
    const repository = createMemoryTaskRepository();
    const task = taskFixture({ id: "task-1" });

    const inserted = await repository.insert(task);
    const listed = await repository.list();

    expect(inserted.ok).toBe(true);
    expect(listed.ok).toBe(true);
    if (!inserted.ok || !listed.ok) return;
    expect(inserted.value.id).toBe("task-1");
    expect(listed.value.map((item) => item.id)).toContain("task-1");
  });

  it("exposes the contract from both repository factories", () => {
    const repositories: TaskRepository[] = [
      createMemoryTaskRepository(),
      createD1TaskRepository(unusedD1Database),
    ];

    for (const repository of repositories) {
      expect(Object.keys(repository).sort()).toEqual(repositoryMethods);
    }
  });
});
