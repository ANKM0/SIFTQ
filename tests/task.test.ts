import { describe, expect, it } from "vitest";
import {
  changeTaskArea,
  changeTaskStatus,
  createTask,
  seedTasks,
  sortForMatrix,
  updateTask,
} from "../src/task";
import type { Task } from "../src/task";

const baseTask: Task = {
  id: "t1",
  title: "base",
  description: "",
  status: "do",
  area: 1,
  order: 0,
};

describe("createTask", () => {
  it("creates a do task in area 1 with the given title", () => {
    const task = createTask({ title: "Write tests" });

    expect(task.title).toBe("Write tests");
    expect(task.status).toBe("do");
    expect(task.area).toBe(1);
    expect(task.id.length).toBeGreaterThan(0);
  });
});

describe("updateTask", () => {
  it("updates title and description without mutating the input", () => {
    const updated = updateTask(baseTask, { title: "renamed", description: "desc" });

    expect(updated.title).toBe("renamed");
    expect(updated.description).toBe("desc");
    expect(baseTask.title).toBe("base");
    expect(baseTask.description).toBe("");
  });
});

describe("changeTaskStatus", () => {
  it("changes the status and keeps the area", () => {
    const done = changeTaskStatus(baseTask, "done");
    const skipped = changeTaskStatus(baseTask, "skip");

    expect(done.status).toBe("done");
    expect(done.area).toBe(1);
    expect(skipped.status).toBe("skip");
  });
});

describe("changeTaskArea", () => {
  it("changes the area and keeps the status", () => {
    const moved = changeTaskArea(baseTask, 4);

    expect(moved.area).toBe(4);
    expect(moved.status).toBe("do");
  });
});

describe("sortForMatrix", () => {
  it("returns only do tasks ordered by area then order", () => {
    const tasks: Task[] = [
      { ...baseTask, id: "done", status: "done", area: 4, order: 0 },
      { ...baseTask, id: "skip", status: "skip", area: 1, order: 0 },
      { ...baseTask, id: "a1-late", area: 1, order: 5 },
      { ...baseTask, id: "a2", area: 2, order: 1 },
      { ...baseTask, id: "a1-early", area: 1, order: 0 },
      { ...baseTask, id: "a3", area: 3, order: 0 },
    ];

    expect(sortForMatrix(tasks).map((task) => task.id)).toEqual([
      "a1-early",
      "a1-late",
      "a2",
      "a3",
    ]);
  });
});

describe("seedTasks", () => {
  it("returns only tasks with valid status and area values", () => {
    const tasks = seedTasks();

    for (const task of tasks) {
      expect(["do", "done", "skip"]).toContain(task.status);
      expect([1, 2, 3, 4]).toContain(task.area);
      expect(task.title.length).toBeGreaterThan(0);
    }
  });
});
