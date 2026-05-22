import { describe, expect, it } from "vitest";

import {
  createTask,
  listTasks,
  moveTask,
  reorderTask,
  updateTaskTitle
} from "../../src/application/taskOperations";
import { InMemoryTaskRepository } from "../../src/adapters/inMemoryTaskRepository";

describe("task operations", () => {
  it("creates and lists tasks through the repository port", async () => {
    const repository = new InMemoryTaskRepository({
      generateId: createTestIdGenerator()
    });

    const task = await createTask(repository, { areaId: "do", title: "  First  " });

    expect(task).toMatchObject({
      id: "operation-task-1",
      title: "First",
      areaId: "do",
      status: "active",
      order: 0
    });
    expect(await listTasks(repository)).toEqual([task]);
  });

  it("rejects invalid titles before they appear in operation results", async () => {
    const repository = new InMemoryTaskRepository();

    await expect(createTask(repository, { areaId: "do", title: "   " })).rejects.toThrow(
      "Task title must not be empty."
    );
    await expect(
      createTask(repository, { areaId: "do", title: "a".repeat(257) })
    ).rejects.toThrow("Task title must be 256 characters or less.");

    expect(await listTasks(repository)).toEqual([]);
  });

  it("keeps duplicate titles distinct by task id", async () => {
    const repository = new InMemoryTaskRepository({
      generateId: createTestIdGenerator()
    });

    const firstTask = await createTask(repository, {
      areaId: "do",
      title: "Duplicate"
    });
    const secondTask = await createTask(repository, {
      areaId: "do",
      title: "Duplicate"
    });

    expect(firstTask.title).toBe(secondTask.title);
    expect(firstTask.id).not.toBe(secondTask.id);
  });

  it("updates only the task title through the repository port", async () => {
    const repository = new InMemoryTaskRepository({
      generateId: createTestIdGenerator()
    });
    const task = await createTask(repository, {
      areaId: "schedule",
      title: "Original"
    });

    const updatedTask = await updateTaskTitle(repository, {
      taskId: task.id,
      title: "  Revised  "
    });

    expect(updatedTask).toEqual({
      ...task,
      title: "Revised"
    });
    expect(await listTasks(repository)).toEqual([updatedTask]);
  });

  it("rejects invalid updated titles and keeps the original task", async () => {
    const repository = new InMemoryTaskRepository({
      generateId: createTestIdGenerator()
    });
    const task = await createTask(repository, { areaId: "do", title: "Original" });

    await expect(
      updateTaskTitle(repository, { taskId: task.id, title: "   " })
    ).rejects.toThrow("Task title must not be empty.");
    await expect(
      updateTaskTitle(repository, { taskId: task.id, title: "a".repeat(257) })
    ).rejects.toThrow("Task title must be 256 characters or less.");

    expect(await listTasks(repository)).toEqual([task]);
  });

  it("moves tasks between areas and reorders tasks inside an area", async () => {
    const repository = new InMemoryTaskRepository({
      generateId: createTestIdGenerator()
    });
    const firstTask = await createTask(repository, { areaId: "do", title: "First" });
    const movedTask = await createTask(repository, { areaId: "do", title: "Moved" });
    const targetTask = await createTask(repository, {
      areaId: "schedule",
      title: "Target"
    });

    await moveTask(repository, {
      taskId: movedTask.id,
      toAreaId: "schedule",
      insertAt: 0
    });
    await reorderTask(repository, { taskId: targetTask.id, toIndex: 0 });

    expect(await listTasks(repository)).toMatchObject([
      { id: firstTask.id, areaId: "do", order: 0 },
      { id: targetTask.id, areaId: "schedule", order: 0 },
      { id: movedTask.id, areaId: "schedule", order: 1 }
    ]);
  });
});

function createTestIdGenerator(): () => string {
  let nextId = 1;

  return () => `operation-task-${nextId++}`;
}
