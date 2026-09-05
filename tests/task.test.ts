import { describe, expect, it } from "vite-plus/test";
import {
  TASK_TITLE_MAX_CODE_POINTS,
  changeTaskArea,
  changeTaskStatus,
  createTask,
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
