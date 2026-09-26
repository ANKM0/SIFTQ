import { describe, expect, it } from "vite-plus/test";
import { PREVIEW_TASKS } from "../src/preview/tasks";
import { TASK_LIST_PAGE_SIZE } from "../src/task-list";

describe("PREVIEW_TASKS", () => {
  it("keeps the seed scenario covering all matrix areas and task states first", () => {
    expect(PREVIEW_TASKS.slice(0, 4).map((task) => task.area)).toEqual([1, 2, 3, 4]);
    expect(PREVIEW_TASKS.slice(0, 4).map((task) => task.status)).toEqual([
      "do",
      "do",
      "done",
      "skip",
    ]);
  });

  it("provides at least three list pages per status", () => {
    for (const status of ["do", "done", "skip"] as const) {
      const count = PREVIEW_TASKS.filter((task) => task.status === status).length;
      expect(count).toBeGreaterThan(TASK_LIST_PAGE_SIZE * 2);
    }
  });
});
