import { type Modifier } from "@dnd-kit/core";

import { INITIAL_AREAS, type AreaId, type MatrixAreaId, isMatrixArea } from "../domain/area";
import { type Task, type TaskId } from "../domain/task";

export type TaskDropOperation =
  | {
      readonly type: "move";
      readonly taskId: TaskId;
      readonly toAreaId: AreaId;
      readonly insertAt: number;
    }
  | {
      readonly type: "reorder";
      readonly taskId: TaskId;
      readonly toIndex: number;
    };

export function areaDropId(areaId: AreaId): string {
  return `area:${areaId}`;
}

export function taskDropId(taskId: TaskId): string {
  return `task:${taskId}`;
}

export const restrictDragToWindowEdges: Modifier = ({
  draggingNodeRect,
  transform,
  windowRect
}) => {
  if (draggingNodeRect === null || windowRect === null) {
    return transform;
  }

  return {
    ...transform,
    x: clamp(
      transform.x,
      windowRect.left - draggingNodeRect.left,
      windowRect.right - draggingNodeRect.right
    ),
    y: clamp(
      transform.y,
      windowRect.top - draggingNodeRect.top,
      windowRect.bottom - draggingNodeRect.bottom
    )
  };
};

export function resolveTaskDropOperation(
  tasks: readonly Task[],
  activeDropId: string,
  overDropId: string | null
): TaskDropOperation | null {
  const taskId = taskIdFromDropId(activeDropId);

  if (taskId === null || overDropId === null) {
    return null;
  }

  const activeTask = tasks.find((task) => task.id === taskId);

  if (activeTask === undefined || !isMatrixArea(activeTask.areaId)) {
    return null;
  }

  const targetAreaId = areaIdFromDropId(overDropId);

  if (targetAreaId !== null) {
    const insertAt = tasksInArea(tasks, targetAreaId).length;

    return operationForTarget(taskId, activeTask.areaId, targetAreaId, insertAt);
  }

  const targetTaskId = taskIdFromDropId(overDropId);
  const targetTask = tasks.find((task) => task.id === targetTaskId);

  if (targetTask === undefined || !isMatrixArea(targetTask.areaId)) {
    return null;
  }

  const insertAt = tasksInArea(tasks, targetTask.areaId).findIndex(
    (task) => task.id === targetTask.id
  );

  return operationForTarget(taskId, activeTask.areaId, targetTask.areaId, insertAt);
}

function operationForTarget(
  taskId: TaskId,
  fromAreaId: MatrixAreaId,
  toAreaId: AreaId,
  insertAt: number
): TaskDropOperation | null {
  if (insertAt < 0) {
    return null;
  }

  if (fromAreaId === toAreaId) {
    return { type: "reorder", taskId, toIndex: insertAt };
  }

  return { type: "move", taskId, toAreaId, insertAt };
}

function tasksInArea(tasks: readonly Task[], areaId: AreaId): Task[] {
  return tasks
    .filter((task) => task.areaId === areaId)
    .sort((left, right) => left.order - right.order);
}

function areaIdFromDropId(dropId: string): AreaId | null {
  const areaId = dropId.replace(/^area:/, "");

  if (areaId === dropId || !isAreaId(areaId)) {
    return null;
  }

  return areaId;
}

function isAreaId(areaId: string): areaId is AreaId {
  return INITIAL_AREAS.some((area) => area.id === areaId);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function taskIdFromDropId(dropId: string): TaskId | null {
  const taskId = dropId.replace(/^task:/, "");

  return taskId === dropId || taskId.length === 0 ? null : taskId;
}
