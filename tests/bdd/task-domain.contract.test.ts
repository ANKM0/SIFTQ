import { describe, expect, it } from "vite-plus/test";
import {
  changeTaskArea,
  changeTaskStatus,
  createTask,
  moveTask,
  sortForMatrix,
} from "../../src/task";
import type { Task } from "../../src/task";
import { taskFixture } from "../helpers/task-fixture";

describe("BDD-TM-001: domain task creation", () => {
  it("creates a task with display and edit attributes", () => {
    const result = createTask({
      owner_id: "owner-1",
      title: "Buy milk",
      description: "low-fat",
    });

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.title).toBe("Buy milk");
    expect(result.value.description).toBe("low-fat");
    expect(result.value.status).toBe("do");
    expect(result.value.area).toBe(1);
    expect(result.value.order).toBe(1);
    expect(result.value.version).toBe(1);
    expect(result.value.id).toEqual(expect.any(String));
    expect(result.value.owner_id).toBe("owner-1");
  });
});

describe("BDD-TM-002 / BDD-TM-003 / BDD-TM-004: matrix extraction", () => {
  it("shows only do tasks in the matrix", () => {
    const tasks = [
      taskFixture({ id: "do-1", status: "do", area: 1, order: 1 }),
      taskFixture({ id: "done-1", status: "done", area: 1, order: 2 }),
      taskFixture({ id: "skip-1", status: "skip", area: 1, order: 3 }),
    ];

    const matrix = sortForMatrix(tasks);

    expect(matrix.map((task) => task.id)).toEqual(["do-1"]);
  });

  it("groups do tasks by area and preserves area order", () => {
    const tasks = [
      taskFixture({ id: "area-4", status: "do", area: 4, order: 0 }),
      taskFixture({ id: "area-1", status: "do", area: 1, order: 0 }),
      taskFixture({ id: "area-2", status: "do", area: 2, order: 0 }),
    ];

    const matrix = sortForMatrix(tasks);

    expect(matrix.map((task) => task.area)).toEqual([1, 2, 4]);
  });
});

describe("BDD-TM-007: status change preserves area", () => {
  it("keeps area when a task is completed or skipped", () => {
    const task = taskFixture({ id: "task-1", area: 3 });

    const done = changeTaskStatus(task, "done");
    expect(done.ok).toBe(true);
    if (!done.ok) return;
    expect(done.value.area).toBe(3);

    const backToDo = changeTaskStatus(done.value, "do");
    expect(backToDo.ok).toBe(true);
    if (!backToDo.ok) return;
    expect(backToDo.value.area).toBe(3);
  });
});

describe("BDD-TM-008: domain reorder", () => {
  it("moves a task to another area and order", () => {
    const tasks: readonly Task[] = [
      taskFixture({ id: "task-1", area: 1, order: 0 }),
      taskFixture({ id: "task-2", area: 1, order: 1 }),
    ];

    const moved = moveTask(tasks, "task-1", 2, 0);

    const movedTask = moved.find((task) => task.id === "task-1");
    expect(movedTask).toBeDefined();
    expect(movedTask?.area).toBe(2);
    expect(movedTask?.order).toBe(0);
  });
});

describe("BDD-TM-006: domain area change", () => {
  it("changes only the area", () => {
    const task = taskFixture({ id: "task-1", area: 1 });

    const result = changeTaskArea(task, 4);

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.area).toBe(4);
    expect(result.value.status).toBe("do");
  });
});
