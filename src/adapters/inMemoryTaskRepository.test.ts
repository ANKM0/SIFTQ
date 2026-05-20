import { describe, expect, it } from "vitest";

import {
  createTask,
  listTasks,
  moveTask,
  reorderTask
} from "../application/taskOperations";
import { isTaskVisibleInMatrix } from "../domain/task";
import { InMemoryTaskRepository } from "./inMemoryTaskRepository";

describe("InMemoryTaskRepository", () => {
  it("creates tasks at the end of the target matrix area", async () => {
    const repository = new InMemoryTaskRepository({
      generateId: createTestIdGenerator()
    });

    await createTask(repository, { title: "First", areaId: "do" });
    await createTask(repository, { title: "Other area", areaId: "schedule" });
    await createTask(repository, { title: "Second", areaId: "do" });

    expect(await listTasks(repository)).toMatchObject([
      { title: "First", areaId: "do", status: "active", order: 0 },
      { title: "Second", areaId: "do", status: "active", order: 1 },
      { title: "Other area", areaId: "schedule", status: "active", order: 0 }
    ]);
  });

  it("allows duplicate titles because tasks are identified by id", async () => {
    const repository = new InMemoryTaskRepository({
      generateId: createTestIdGenerator()
    });

    const firstTask = await createTask(repository, {
      title: "Duplicate",
      areaId: "do"
    });
    const secondTask = await createTask(repository, {
      title: "Duplicate",
      areaId: "do"
    });

    expect(firstTask.title).toBe(secondTask.title);
    expect(firstTask.id).not.toBe(secondTask.id);
  });

  it("rejects direct creation in terminal areas", async () => {
    const repository = new InMemoryTaskRepository();

    await expect(
      createTask(repository, {
        title: "Terminal",
        areaId: "done"
      } as unknown as Parameters<typeof createTask>[1])
    ).rejects.toThrow("Tasks can only be created in matrix areas.");
  });

  it("moves tasks between matrix areas at an arbitrary insertion position", async () => {
    const repository = new InMemoryTaskRepository({
      generateId: createTestIdGenerator()
    });
    const firstTask = await createTask(repository, { title: "First", areaId: "do" });
    const secondTask = await createTask(repository, {
      title: "Second",
      areaId: "do"
    });
    const targetTopTask = await createTask(repository, {
      title: "Target top",
      areaId: "schedule"
    });
    const targetBottomTask = await createTask(repository, {
      title: "Target bottom",
      areaId: "schedule"
    });

    await moveTask(repository, {
      taskId: secondTask.id,
      toAreaId: "schedule",
      insertAt: 1
    });

    expect(await listTasks(repository)).toMatchObject([
      { id: firstTask.id, areaId: "do", order: 0 },
      { id: targetTopTask.id, areaId: "schedule", order: 0 },
      { id: secondTask.id, areaId: "schedule", order: 1 },
      { id: targetBottomTask.id, areaId: "schedule", order: 2 }
    ]);
  });

  it("reorders tasks inside the same matrix area", async () => {
    const repository = new InMemoryTaskRepository({
      generateId: createTestIdGenerator()
    });
    const firstTask = await createTask(repository, { title: "First", areaId: "do" });
    const secondTask = await createTask(repository, {
      title: "Second",
      areaId: "do"
    });
    const thirdTask = await createTask(repository, { title: "Third", areaId: "do" });

    await reorderTask(repository, { taskId: thirdTask.id, toIndex: 0 });

    expect(await listTasks(repository)).toMatchObject([
      { id: thirdTask.id, areaId: "do", order: 0 },
      { id: firstTask.id, areaId: "do", order: 1 },
      { id: secondTask.id, areaId: "do", order: 2 }
    ]);
  });

  it("updates status and hides tasks moved to Done or Skipped", async () => {
    const repository = new InMemoryTaskRepository({
      generateId: createTestIdGenerator()
    });
    const doneTask = await createTask(repository, { title: "Finish", areaId: "do" });
    const skippedTask = await createTask(repository, {
      title: "Drop",
      areaId: "delegate"
    });

    await moveTask(repository, { taskId: doneTask.id, toAreaId: "done" });
    await moveTask(repository, { taskId: skippedTask.id, toAreaId: "skipped" });

    const tasks = await listTasks(repository);

    expect(tasks).toMatchObject([
      { id: skippedTask.id, areaId: "skipped", status: "skipped", order: 0 },
      { id: doneTask.id, areaId: "done", status: "done", order: 0 }
    ]);
    expect(tasks.every((task) => !isTaskVisibleInMatrix(task))).toBe(true);
  });

  it("does not restore terminal tasks to matrix areas in the v1 operation", async () => {
    const repository = new InMemoryTaskRepository({
      generateId: createTestIdGenerator()
    });
    const doneTask = await createTask(repository, { title: "Finish", areaId: "do" });

    await moveTask(repository, { taskId: doneTask.id, toAreaId: "done" });

    await expect(
      moveTask(repository, { taskId: doneTask.id, toAreaId: "do" })
    ).rejects.toThrow("Terminal tasks cannot be restored to matrix areas.");
  });

  it("lists tasks in initial area order after status transitions", async () => {
    const repository = new InMemoryTaskRepository({
      generateId: createTestIdGenerator()
    });
    const doTask = await createTask(repository, { title: "Do", areaId: "do" });
    const scheduleTask = await createTask(repository, {
      title: "Schedule",
      areaId: "schedule"
    });
    const delegateTask = await createTask(repository, {
      title: "Delegate",
      areaId: "delegate"
    });
    const eliminateTask = await createTask(repository, {
      title: "Eliminate",
      areaId: "eliminate"
    });

    await moveTask(repository, { taskId: delegateTask.id, toAreaId: "skipped" });
    await moveTask(repository, { taskId: eliminateTask.id, toAreaId: "done" });

    expect((await listTasks(repository)).map((task) => task.areaId)).toEqual([
      "do",
      "schedule",
      "skipped",
      "done"
    ]);
    expect(doTask.areaId).toBe("do");
    expect(scheduleTask.areaId).toBe("schedule");
  });

  it("rejects invalid task titles before adding a task", async () => {
    const repository = new InMemoryTaskRepository();

    await expect(
      createTask(repository, { title: "   ", areaId: "do" })
    ).rejects.toThrow("Task title must not be empty.");

    expect(await listTasks(repository)).toEqual([]);
  });

  it("rejects titles longer than 256 characters before adding a task", async () => {
    const repository = new InMemoryTaskRepository();

    await expect(
      createTask(repository, { title: "a".repeat(257), areaId: "do" })
    ).rejects.toThrow("Task title must be 256 characters or less.");

    expect(await listTasks(repository)).toEqual([]);
  });
});

function createTestIdGenerator(): () => string {
  let nextId = 1;

  return () => `test-task-${nextId++}`;
}
