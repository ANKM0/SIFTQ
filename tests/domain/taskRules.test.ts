import { describe, expect, it } from "vitest";

import { type Task } from "../../src/contracts/task";
import {
  buildBulkDeleteConfirmation,
  buildDeleteTaskConfirmation,
  deleteTasksAndNormalizeOrder,
  formatSelectedTaskCount,
  pruneSelectedTaskIds,
  toggleTaskSelection
} from "../../src/domain/taskRules";

describe("taskRules", () => {
  it("builds delete confirmation copy", () => {
    expect(buildDeleteTaskConfirmation({ title: "Visible" })).toBe('"Visible" を削除しますか?');
    expect(buildBulkDeleteConfirmation(2)).toBe("2件のタスクを削除しますか?");
    expect(formatSelectedTaskCount(3)).toBe("3件選択中");
  });

  it("toggles task selection without duplicating ids", () => {
    expect(toggleTaskSelection([], "task-1", true)).toEqual(["task-1"]);
    expect(toggleTaskSelection(["task-1"], "task-1", true)).toEqual(["task-1"]);
    expect(toggleTaskSelection(["task-1", "task-2"], "task-1", false)).toEqual(["task-2"]);
  });

  it("prunes selection ids that no longer exist", () => {
    expect(
      pruneSelectedTaskIds(["task-1", "task-2"], [
        { id: "task-2" },
        { id: "task-3" }
      ])
    ).toEqual(["task-2"]);
  });

  it("deletes tasks and normalizes list and matrix order", () => {
    const tasks = [
      task({ id: "task-1", title: "Do first", areaId: "do", order: 0, listOrder: 0 }),
      task({
        id: "task-2",
        title: "Schedule first",
        areaId: "schedule",
        order: 0,
        listOrder: 1
      }),
      task({ id: "task-3", title: "Do second", areaId: "do", order: 1, listOrder: 2 }),
      task({
        id: "task-4",
        title: "Schedule second",
        areaId: "schedule",
        order: 1,
        listOrder: 3
      }),
      task({ id: "task-5", title: "Do third", areaId: "do", order: 2, listOrder: 4 })
    ] satisfies Task[];

    expect(
      deleteTasksAndNormalizeOrder(tasks, new Set(["task-1", "task-4"]), "2026-07-16T00:00:00.000Z")
    ).toEqual([
      task({
        id: "task-2",
        title: "Schedule first",
        areaId: "schedule",
        order: 0,
        listOrder: 0,
        updatedAt: "2026-07-16T00:00:00.000Z"
      }),
      task({
        id: "task-3",
        title: "Do second",
        areaId: "do",
        order: 0,
        listOrder: 1,
        updatedAt: "2026-07-16T00:00:00.000Z"
      }),
      task({
        id: "task-5",
        title: "Do third",
        areaId: "do",
        order: 1,
        listOrder: 2,
        updatedAt: "2026-07-16T00:00:00.000Z"
      })
    ]);
  });
});

function task(input: Partial<Task> & Pick<Task, "id" | "title">): Task {
  const areaId = input.areaId ?? "do";

  return {
    areaId,
    createdAt: "2024-01-01T00:00:00.000Z",
    description: "",
    listOrder: input.listOrder ?? 0,
    order: input.order ?? 0,
    status: areaId === "done" ? "done" : areaId === "skipped" ? "skipped" : "active",
    updatedAt: "2024-01-01T00:00:00.000Z",
    ...input
  };
}
