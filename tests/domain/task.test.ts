import { describe, expect, it } from "vitest";

import { INITIAL_AREAS } from "../../src/domain/area";
import {
  isTaskVisibleInMatrix,
  normalizeTaskTitle,
  statusForArea,
  TaskValidationError,
  TASK_TITLE_MAX_LENGTH,
  type Task
} from "../../src/domain/task";

describe("area domain", () => {
  it("defines the four matrix areas and two terminal areas", () => {
    expect(INITIAL_AREAS).toEqual([
      { id: "do", label: "Do", kind: "matrix", role: "do" },
      { id: "schedule", label: "Schedule", kind: "matrix", role: "schedule" },
      { id: "delegate", label: "Delegate", kind: "matrix", role: "delegate" },
      { id: "eliminate", label: "Eliminate", kind: "matrix", role: "eliminate" },
      { id: "skipped", label: "Skipped", kind: "terminal", role: "skipped" },
      { id: "done", label: "Done", kind: "terminal", role: "done" }
    ]);
  });
});

describe("task domain", () => {
  it("normalizes valid titles without enforcing uniqueness", () => {
    expect(normalizeTaskTitle("  duplicate title  ")).toBe("duplicate title");
    expect(normalizeTaskTitle("duplicate title")).toBe("duplicate title");
  });

  it("rejects blank and too-long titles", () => {
    expect(() => normalizeTaskTitle("   ")).toThrow(TaskValidationError);
    expect(() => normalizeTaskTitle("a".repeat(TASK_TITLE_MAX_LENGTH + 1))).toThrow(
      TaskValidationError
    );
  });

  it("derives status and matrix visibility from the current area", () => {
    expect(statusForArea("do")).toBe("active");
    expect(statusForArea("done")).toBe("done");
    expect(statusForArea("skipped")).toBe("skipped");

    const activeTask: Task = {
      id: "task-1",
      title: "Visible",
      areaId: "do",
      status: "active",
      order: 0
    };
    const doneTask: Task = {
      ...activeTask,
      areaId: "done",
      status: "done"
    };
    const skippedTask: Task = {
      ...activeTask,
      areaId: "skipped",
      status: "skipped"
    };

    expect(isTaskVisibleInMatrix(activeTask)).toBe(true);
    expect(isTaskVisibleInMatrix(doneTask)).toBe(false);
    expect(isTaskVisibleInMatrix(skippedTask)).toBe(false);
  });
});
