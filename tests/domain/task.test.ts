import { describe, expect, it } from "vitest";

import {
  INITIAL_AREAS,
  isTaskVisibleInMatrix,
  normalizeTaskTitleInput,
  validateTaskTitleInput
} from "../../src/ui/taskPresentation";
import {
  TASK_TITLE_MAX_LENGTH,
  type Task
} from "../../src/contracts/task";

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
  it("normalizes valid title input without enforcing uniqueness", () => {
    expect(normalizeTaskTitleInput("  duplicate title  ")).toBe("duplicate title");
    expect(normalizeTaskTitleInput("duplicate title")).toBe("duplicate title");
  });

  it("rejects blank and too-long titles", () => {
    expect(validateTaskTitleInput("   ")).toBe("Task title must not be empty.");
    expect(validateTaskTitleInput("a".repeat(TASK_TITLE_MAX_LENGTH + 1))).toBe(
      "Title must be 256 characters or less."
    );
  });

  it("derives matrix visibility from task status and current area", () => {
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
