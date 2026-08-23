import { describe, expect, it } from "vitest";
import {
  changeTaskArea,
  changeTaskStatus,
  createTask,
  moveTask,
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
  version: 1,
};

describe("createTask", () => {
  it("creates a do task in area 1 with the given title", () => {
    const task = createTask({ title: "Write tests" });

    expect(task.title).toBe("Write tests");
    expect(task.status).toBe("do");
    expect(task.area).toBe(1);
    expect(task.version).toBe(1);
    expect(task.id.length).toBeGreaterThan(0);
  });
});

describe("updateTask", () => {
  it("updates title and description without mutating the input", () => {
    const updated = updateTask(baseTask, { title: "renamed", description: "desc" });

    expect(updated.title).toBe("renamed");
    expect(updated.description).toBe("desc");
    expect(updated.version).toBe(baseTask.version);
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

describe("moveTask", () => {
  it("reorders tasks inside the same area without mutating the input", () => {
    const tasks: Task[] = [
      { ...baseTask, id: "a", area: 1, order: 0 },
      { ...baseTask, id: "b", area: 1, order: 1 },
    ];

    const moved = moveTask(tasks, "a", 1, 1);

    expect(moved.map((task) => task.id)).toEqual(["b", "a"]);
    expect(moved.filter((task) => task.area === 1).map((task) => task.order)).toEqual([
      0, 1,
    ]);
    expect(tasks.map((task) => task.id)).toEqual(["a", "b"]);
  });

  it("moves a task to another area and normalizes the target order", () => {
    const tasks: Task[] = [
      { ...baseTask, id: "a", area: 1, order: 0 },
      { ...baseTask, id: "b", area: 1, order: 1 },
      { ...baseTask, id: "c", area: 2, order: 0 },
    ];

    const moved = moveTask(tasks, "b", 2, 0);

    expect(moved.find((task) => task.id === "b")).toMatchObject({
      area: 2,
      order: 0,
    });
    expect(
      moved
        .filter((task) => task.area === 2)
        .map((task) => task.id),
    ).toEqual(["b", "c"]);
  });

  it("returns a copy unchanged when the task is missing", () => {
    const tasks: Task[] = [{ ...baseTask }];

    const moved = moveTask(tasks, "missing", 2, 0);

    expect(moved).toEqual(tasks);
    expect(moved).not.toBe(tasks);
  });

  it("clamps an out-of-range order to the end of the area list", () => {
    const tasks: Task[] = [
      { ...baseTask, id: "a", area: 1, order: 0 },
      { ...baseTask, id: "b", area: 1, order: 1 },
      { ...baseTask, id: "c", area: 1, order: 2 },
    ];

    const moved = moveTask(tasks, "a", 1, 99);

    expect(moved.map((task) => task.id)).toEqual(["b", "c", "a"]);
    expect(moved.map((task) => task.order)).toEqual([0, 1, 2]);
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
