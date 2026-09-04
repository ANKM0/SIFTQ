import { describe, expect, it } from "vite-plus/test";
import {
  TASK_TITLE_MAX_CODE_POINTS,
  changeTaskArea,
  changeTaskStatus,
  createTask,
  isMatrixSortKey,
  isTaskArea,
  isTaskStatus,
  isTaskTitleValid,
  moveTask,
  sortForMatrix,
  titleCodePointLength,
} from "../src/task";
import { taskFixture } from "./helpers/task-fixture";

describe("task title validation", () => {
  it("counts Unicode code points", () => {
    expect(titleCodePointLength("a😀")).toBe(2);
  });

  it("accepts 1 to 256 Unicode code points", () => {
    expect(isTaskTitleValid("a")).toBe(true);
    expect(isTaskTitleValid("a".repeat(TASK_TITLE_MAX_CODE_POINTS))).toBe(true);
    expect(isTaskTitleValid("😀".repeat(TASK_TITLE_MAX_CODE_POINTS))).toBe(true);

    expect(isTaskTitleValid("")).toBe(false);
    expect(isTaskTitleValid("a".repeat(TASK_TITLE_MAX_CODE_POINTS + 1))).toBe(false);
    expect(isTaskTitleValid("😀".repeat(TASK_TITLE_MAX_CODE_POINTS + 1))).toBe(false);
  });
});

describe("task enums", () => {
  it("recognizes valid status and area values", () => {
    expect(isTaskStatus("do")).toBe(true);
    expect(isTaskStatus("done")).toBe(true);
    expect(isTaskStatus("skip")).toBe(true);
    expect(isTaskStatus("unknown")).toBe(false);

    expect(isTaskArea(1)).toBe(true);
    expect(isTaskArea(4)).toBe(true);
    expect(isTaskArea(0)).toBe(false);
    expect(isTaskArea(5)).toBe(false);
  });
});

describe("task domain", () => {
  it("creates a task and rejects an invalid title", () => {
    const created = createTask({
      owner_id: "owner-1",
      title: "Buy milk",
      description: "",
    });

    expect(created.ok).toBe(true);
    if (!created.ok) return;
    expect(created.value.status).toBe("do");
    expect(created.value.area).toBe(1);
    expect(created.value.order).toBe(1);
    expect(created.value.version).toBe(1);

    const invalid = createTask({
      owner_id: "owner-1",
      title: "",
      description: "",
    });
    expect(invalid.ok).toBe(false);
    if (!invalid.ok) {
      expect(invalid.error.code).toBe("INVALID_TITLE");
    }
  });

  it("keeps area when status changes", () => {
    const task = taskFixture({ id: "task-1", area: 3 });

    const done = changeTaskStatus(task, "done");
    expect(done.ok).toBe(true);
    if (!done.ok) return;
    expect(done.value.area).toBe(3);
    expect(done.value.status).toBe("done");
  });

  it("changes area without changing status", () => {
    const task = taskFixture({ id: "task-1", status: "do" });

    const changed = changeTaskArea(task, 4);
    expect(changed.ok).toBe(true);
    if (!changed.ok) return;
    expect(changed.value.area).toBe(4);
    expect(changed.value.status).toBe("do");
  });

  it("sorts matrix tasks by area and order", () => {
    const tasks = [
      taskFixture({ id: "b", status: "do", area: 2, order: 0 }),
      taskFixture({ id: "a", status: "do", area: 1, order: 2 }),
      taskFixture({ id: "c", status: "do", area: 1, order: 1 }),
      taskFixture({ id: "done", status: "done", area: 1, order: 0 }),
    ];

    expect(sortForMatrix(tasks).map((task) => task.id)).toEqual(["c", "a", "b"]);
  });
});

describe("matrix display sort", () => {
  it("recognizes valid sort keys", () => {
    expect(isMatrixSortKey("order")).toBe(true);
    expect(isMatrixSortKey("title")).toBe(true);
    expect(isMatrixSortKey("created_at")).toBe(true);
    expect(isMatrixSortKey("updated_at")).toBe(true);
    expect(isMatrixSortKey("status")).toBe(false);
    expect(isMatrixSortKey(undefined)).toBe(false);
  });

  it("sorts by title within each area without changing area or order", () => {
    const tasks = [
      taskFixture({ id: "z", title: "Zebra", status: "do", area: 1, order: 0 }),
      taskFixture({ id: "a", title: "Apple", status: "do", area: 1, order: 1 }),
      taskFixture({ id: "b", title: "Banana", status: "do", area: 2, order: 0 }),
    ];

    const sorted = sortForMatrix(tasks, "title");

    expect(sorted.map((task) => task.id)).toEqual(["a", "z", "b"]);
    expect(sorted.map((task) => [task.area, task.order])).toEqual([
      [1, 1],
      [1, 0],
      [2, 0],
    ]);
  });

  it("sorts by created_at and updated_at within an area", () => {
    const tasks = [
      taskFixture({ id: "new", created_at: "2026-02-01T00:00:00.000Z", updated_at: "2026-02-01T00:00:00.000Z" }),
      taskFixture({ id: "old", created_at: "2026-01-01T00:00:00.000Z", updated_at: "2026-01-01T00:00:00.000Z" }),
    ];

    expect(sortForMatrix(tasks, "created_at").map((task) => task.id)).toEqual(["old", "new"]);
    expect(sortForMatrix(tasks, "updated_at").map((task) => task.id)).toEqual(["old", "new"]);
  });
});

describe("task move", () => {
  it("normalizes order when moving to another area", () => {
    const tasks = [
      taskFixture({ id: "task-1", area: 1, order: 0 }),
      taskFixture({ id: "task-2", area: 1, order: 1 }),
      taskFixture({ id: "task-3", area: 1, order: 2 }),
      taskFixture({ id: "task-4", area: 2, order: 0 }),
    ];

    const moved = moveTask(tasks, "task-1", 2, 1);

    expect(moved.ok).toBe(true);
    if (!moved.ok) return;
    expect(moved.value).toHaveLength(4);
    expect(moved.value.find((task) => task.id === "task-1")?.order).toBe(1);
    expect(moved.value.find((task) => task.id === "task-4")?.order).toBe(0);
    expect(moved.value.filter((task) => task.area === 1).map((task) => task.order)).toEqual([0, 1]);
  });

  it("rejects invalid move input", () => {
    const tasks = [taskFixture({ id: "task-1" })];

    expect(moveTask(tasks, "missing", 1, 0).ok).toBe(false);
    expect(moveTask(tasks, "task-1", 1, -1).ok).toBe(false);
  });
});
