import { describe, expect, it } from "vite-plus/test";
import { PREVIEW_TASKS } from "../src/preview/tasks";

describe("PREVIEW_TASKS", () => {
  it("provides a fixed scenario covering all matrix areas and task states", () => {
    expect(PREVIEW_TASKS).toHaveLength(4);
    expect(PREVIEW_TASKS.map((task) => task.area)).toEqual([1, 2, 3, 4]);
    expect(PREVIEW_TASKS.map((task) => task.status)).toEqual(["do", "do", "done", "skip"]);
  });
});
