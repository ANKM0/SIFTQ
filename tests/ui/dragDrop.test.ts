import { describe, expect, it } from "vitest";

import { type Task } from "../../src/domain/task";
import {
  areaDropId,
  resolveTaskDropOperation,
  taskDropId
} from "../../src/ui/dragDrop";

describe("dragDrop", () => {
  it("resolves same-area drops over a task to reorder operations", () => {
    expect(
      resolveTaskDropOperation(
        [
          task({ id: "first", areaId: "do", order: 0 }),
          task({ id: "second", areaId: "do", order: 1 }),
          task({ id: "third", areaId: "do", order: 2 })
        ],
        taskDropId("third"),
        taskDropId("first")
      )
    ).toEqual({ type: "reorder", taskId: "third", toIndex: 0 });
  });

  it("resolves cross-area drops over a task to move operations with insertion", () => {
    expect(
      resolveTaskDropOperation(
        [
          task({ id: "moved", areaId: "do", order: 0 }),
          task({ id: "top", areaId: "schedule", order: 0 }),
          task({ id: "bottom", areaId: "schedule", order: 1 })
        ],
        taskDropId("moved"),
        taskDropId("bottom")
      )
    ).toEqual({
      type: "move",
      taskId: "moved",
      toAreaId: "schedule",
      insertAt: 1
    });
  });

  it("resolves drops over an area to append operations", () => {
    expect(
      resolveTaskDropOperation(
        [
          task({ id: "moved", areaId: "do", order: 0 }),
          task({ id: "existing", areaId: "delegate", order: 0 })
        ],
        taskDropId("moved"),
        areaDropId("delegate")
      )
    ).toEqual({
      type: "move",
      taskId: "moved",
      toAreaId: "delegate",
      insertAt: 1
    });
  });

  it("ignores invalid drops without creating repository operations", () => {
    expect(
      resolveTaskDropOperation(
        [task({ id: "first", areaId: "do", order: 0 })],
        taskDropId("first"),
        null
      )
    ).toBeNull();
    expect(
      resolveTaskDropOperation(
        [task({ id: "first", areaId: "do", order: 0 })],
        taskDropId("first"),
        "task:missing"
      )
    ).toBeNull();
  });
});

function task(input: Pick<Task, "id" | "areaId" | "order">): Task {
  return {
    ...input,
    title: input.id,
    status: input.areaId === "done" ? "done" : "active"
  };
}
