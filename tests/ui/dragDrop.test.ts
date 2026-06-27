import { describe, expect, it } from "vitest";

import { type Task } from "../../src/contracts/task";
import {
  TASK_LIST_DROP_ID,
  areaDropId,
  matrixCollisionDetection,
  resolveTaskListDropIndex,
  resolveTaskDropOperation,
  restrictDragToWindowEdges,
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

  it("resolves downward same-area drops to post-removal reorder indexes", () => {
    expect(
      resolveTaskDropOperation(
        [
          task({ id: "first", areaId: "do", order: 0 }),
          task({ id: "second", areaId: "do", order: 1 }),
          task({ id: "third", areaId: "do", order: 2 })
        ],
        taskDropId("first"),
        taskDropId("third")
      )
    ).toEqual({ type: "reorder", taskId: "first", toIndex: 1 });
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

  it("resolves drops over terminal areas to move operations", () => {
    for (const terminalAreaId of ["done", "skipped"] as const) {
      expect(
        resolveTaskDropOperation(
          [task({ id: "moved", areaId: "do", order: 0 })],
          taskDropId("moved"),
          areaDropId(terminalAreaId)
        )
      ).toEqual({
        type: "move",
        taskId: "moved",
        toAreaId: terminalAreaId,
        insertAt: 0
      });
    }
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

  it("resolves task list drops to reordered list indexes", () => {
    expect(
      resolveTaskListDropIndex(
        [
          task({ id: "first", areaId: "do", order: 0 }),
          task({ id: "second", areaId: "done", order: 1 }),
          task({ id: "third", areaId: "delegate", order: 2 })
        ],
        taskDropId("third"),
        taskDropId("first")
      )
    ).toBe(0);

    expect(
      resolveTaskListDropIndex(
        [
          task({ id: "first", areaId: "do", order: 0 }),
          task({ id: "second", areaId: "done", order: 1 }),
          task({ id: "third", areaId: "delegate", order: 2 })
        ],
        taskDropId("first"),
        taskDropId("third")
      )
    ).toBe(1);

    expect(
      resolveTaskListDropIndex(
        [
          task({ id: "first", areaId: "do", order: 0 }),
          task({ id: "second", areaId: "done", order: 1 }),
          task({ id: "third", areaId: "delegate", order: 2 })
        ],
        taskDropId("first"),
        TASK_LIST_DROP_ID
      )
    ).toBe(2);
  });

  it("clamps drag movement to the current window edges", () => {
    expect(
      restrictDragToWindowEdges({
        activatorEvent: null,
        active: null,
        activeNodeRect: null,
        containerNodeRect: null,
        draggingNodeRect: {
          bottom: 120,
          height: 100,
          left: 20,
          right: 120,
          top: 20,
          width: 100
        },
        over: null,
        overlayNodeRect: null,
        scrollableAncestors: [],
        scrollableAncestorRects: [],
        transform: { x: 1000, y: 1000, scaleX: 1, scaleY: 1 },
        windowRect: {
          bottom: 300,
          height: 300,
          left: 0,
          right: 400,
          top: 0,
          width: 400
        }
      })
    ).toEqual({ x: 280, y: 180, scaleX: 1, scaleY: 1 });
  });

  it("prefers terminal droppables when the pointer is inside a terminal area", () => {
    const collisions = matrixCollisionDetection(
      collisionArgs({
        collisionRect: rect({ left: 260, top: 40, width: 60, height: 60 }),
        droppableRects: [
          [areaDropId("done"), rect({ left: 240, top: 0, width: 120, height: 300 })],
          [areaDropId("do"), rect({ left: 80, top: 0, width: 180, height: 300 })],
          [taskDropId("task-1"), rect({ left: 250, top: 30, width: 70, height: 70 })]
        ],
        pointerCoordinates: { x: 280, y: 120 }
      })
    );

    expect(collisions.map(({ id }) => id)).toEqual([areaDropId("done")]);
  });

  it("treats the full terminal column as a single drop target", () => {
    for (const y of [10, 150, 290]) {
      const collisions = matrixCollisionDetection(
        collisionArgs({
          collisionRect: rect({ left: 20, top: y - 20, width: 40, height: 40 }),
          droppableRects: [
            [areaDropId("skipped"), rect({ left: 0, top: 0, width: 80, height: 300 })],
            [areaDropId("do"), rect({ left: 80, top: 0, width: 220, height: 300 })]
          ],
          pointerCoordinates: { x: 40, y }
        })
      );

      expect(collisions.map(({ id }) => id)).toEqual([areaDropId("skipped")]);
    }
  });

  it("falls back to the default rect-intersection ranking outside terminal areas", () => {
    const collisions = matrixCollisionDetection(
      collisionArgs({
        collisionRect: rect({ left: 120, top: 20, width: 80, height: 80 }),
        droppableRects: [
          [areaDropId("done"), rect({ left: 260, top: 0, width: 120, height: 300 })],
          [areaDropId("do"), rect({ left: 100, top: 0, width: 180, height: 300 })],
          [taskDropId("task-1"), rect({ left: 110, top: 10, width: 120, height: 120 })]
        ],
        pointerCoordinates: { x: 140, y: 60 }
      })
    );

    expect(collisions.map(({ id }) => id)).toEqual([taskDropId("task-1"), areaDropId("do")]);
  });
});

function task(input: Pick<Task, "id" | "areaId" | "order">): Task {
  return {
    ...input,
    createdAt: new Date(0).toISOString(),
    description: "",
    listOrder: input.order,
    title: input.id,
    status:
      input.areaId === "done"
        ? "done"
        : input.areaId === "skipped"
          ? "skipped"
          : "active",
    updatedAt: new Date(0).toISOString()
  };
}

function collisionArgs(input: {
  collisionRect: ReturnType<typeof rect>;
  droppableRects: ReadonlyArray<readonly [string, ReturnType<typeof rect>]>;
  pointerCoordinates: { x: number; y: number } | null;
}) {
  return {
    active: {
      id: taskDropId("active"),
      data: { current: {} },
      rect: {
        current: {
          initial: input.collisionRect,
          translated: input.collisionRect
        }
      }
    },
    collisionRect: input.collisionRect,
    droppableContainers: input.droppableRects.map(([id, droppableRect]) => ({
      data: { current: {} },
      disabled: false,
      id,
      key: id,
      node: { current: null },
      rect: { current: droppableRect }
    })),
    droppableRects: new Map(input.droppableRects),
    pointerCoordinates: input.pointerCoordinates
  } satisfies Parameters<typeof matrixCollisionDetection>[0];
}

function rect(input: {
  left: number;
  top: number;
  width: number;
  height: number;
}) {
  return {
    ...input,
    bottom: input.top + input.height,
    right: input.left + input.width
  };
}
