import { describe, expect, it } from "vite-plus/test";
import {
  TASK_LIST_PAGE_SIZE,
  TASK_TITLE_MAX_CODE_POINTS,
  changeTaskArea,
  changeTaskStatus,
  createTask,
  filterTasks,
  is_do,
  is_done,
  is_skip,
  isTaskArea,
  isTaskStatus,
  isTaskTitleValid,
  moveTask,
  pageNavItems,
  paginateTasks,
  parsePageParam,
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

describe("task filters", () => {
  it("filters tasks by status and supports composing predicates", () => {
    const tasks = [
      taskFixture({ id: "do", status: "do" }),
      taskFixture({ id: "done", status: "done" }),
      taskFixture({ id: "skip", status: "skip" }),
    ];

    expect(filterTasks(tasks, [is_do]).map((task) => task.id)).toEqual(["do"]);
    expect(filterTasks(tasks, [is_done]).map((task) => task.id)).toEqual(["done"]);
    expect(filterTasks(tasks, [is_skip]).map((task) => task.id)).toEqual(["skip"]);
    expect(filterTasks(tasks, [is_do, is_done])).toEqual([]);
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

describe("task list pagination", () => {
  it("fixes the page size to 25", () => {
    expect(TASK_LIST_PAGE_SIZE).toBe(25);
  });

  it("parses only positive integer page params", () => {
    expect(parsePageParam("1")).toBe(1);
    expect(parsePageParam("2")).toBe(2);

    expect(parsePageParam(null)).toBeNull();
    expect(parsePageParam(undefined)).toBeNull();
    expect(parsePageParam("")).toBeNull();
    expect(parsePageParam("0")).toBeNull();
    expect(parsePageParam("-1")).toBeNull();
    expect(parsePageParam("1.5")).toBeNull();
    expect(parsePageParam("abc")).toBeNull();
    expect(parsePageParam("1abc")).toBeNull();
    expect(parsePageParam(2)).toBeNull();
  });

  it("slices 25 items per page and clamps out-of-range pages", () => {
    const tasks = Array.from({ length: 26 }, (_, index) =>
      taskFixture({ id: `task-${index + 1}` }),
    );

    const first = paginateTasks(tasks, 1);
    expect(first.currentPage).toBe(1);
    expect(first.totalPages).toBe(2);
    expect(first.pageTasks.map((task) => task.id)).toEqual(
      tasks.slice(0, 25).map((task) => task.id),
    );

    const second = paginateTasks(tasks, 2);
    expect(second.currentPage).toBe(2);
    expect(second.pageTasks.map((task) => task.id)).toEqual(["task-26"]);

    const overflow = paginateTasks(tasks, 99);
    expect(overflow.currentPage).toBe(2);
    expect(overflow.pageTasks.map((task) => task.id)).toEqual(["task-26"]);

    const below = paginateTasks(tasks, 0);
    expect(below.currentPage).toBe(1);
    expect(below.pageTasks).toHaveLength(25);
  });

  it("keeps a single page for 25 or fewer items", () => {
    expect(paginateTasks([], 1).totalPages).toBe(1);
    expect(paginateTasks(Array.from({ length: 25 }, (_, index) => taskFixture({ id: `t-${index}` })), 3).currentPage).toBe(1);
  });

  it("keeps the first and last pages and collapses gaps", () => {
    expect(pageNavItems(1, 1)).toEqual([1]);
    expect(pageNavItems(1, 2)).toEqual([1, 2]);
    expect(pageNavItems(2, 3)).toEqual([1, 2, 3]);
    expect(pageNavItems(1, 10)).toEqual([1, 2, "ellipsis", 10]);
    expect(pageNavItems(5, 10)).toEqual([1, "ellipsis", 4, 5, 6, "ellipsis", 10]);
    expect(pageNavItems(10, 10)).toEqual([1, "ellipsis", 9, 10]);
  });
});
