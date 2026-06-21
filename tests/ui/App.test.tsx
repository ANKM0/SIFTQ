import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { type Invoke, type InvokeArgs } from "../../src/adapters/tauriInvoke";
import {
  type AreaId,
  type MatrixAreaId,
  type Task,
  type TaskId,
  type TaskStatus
} from "../../src/contracts/task";
import { App } from "../../src/ui/App";
import { areaDropId, taskDropId } from "../../src/ui/dragDrop";

const dndKitMock = vi.hoisted(() => ({
  droppableIds: [] as string[],
  onDragEnd: undefined as ((event: unknown) => void) | undefined
}));

vi.mock("@dnd-kit/core", async () => {
  const React = await vi.importActual<typeof import("react")>("react");

  return {
    DndContext: ({
      children,
      onDragEnd
    }: {
      children: React.ReactNode;
      onDragEnd: (event: unknown) => void;
    }) => {
      dndKitMock.onDragEnd = onDragEnd;

      return React.createElement(React.Fragment, null, children);
    },
    useDraggable: () => ({
      attributes: {},
      isDragging: false,
      listeners: {},
      setNodeRef: vi.fn(),
      transform: null
    }),
    useDroppable: ({ id }: { id: string }) => {
      dndKitMock.droppableIds.push(id);

      return {
        isOver: false,
        setNodeRef: vi.fn()
      };
    }
  };
});

afterEach(() => {
  dndKitMock.droppableIds = [];
  dndKitMock.onDragEnd = undefined;
  installTauriInvoke(undefined);
  cleanup();
});

describe("App", () => {
  it("renders a runtime-required state outside Tauri", async () => {
    render(<App />);

    expect(await screen.findByText("Tauri runtime required")).toBeTruthy();
    expect(screen.getByText("SIFTQ v2 runs as a desktop app. Browser-only startup is not supported.")).toBeTruthy();
  });

  it("renders a storage error when startup health fails", async () => {
    installTauriInvoke(
      async <T,>() =>
        ({
          code: "MIGRATION",
          message: "Unsupported schema version.",
          ok: false
        }) as T
    );

    render(<App />);

    expect(await screen.findByText("Storage error")).toBeTruthy();
    expect(screen.getByText("MIGRATION")).toBeTruthy();
    expect(screen.getByText("Unsupported schema version.")).toBeTruthy();
  });

  it("renders the matrix quadrants and terminal drop areas after Tauri startup", async () => {
    const commands = new FakeTauriCommands();

    commands.seed(
      task({ id: "task-1", title: "Visible", areaId: "do" }),
      task({ id: "task-2", title: "Hidden", areaId: "done", status: "done" })
    );
    installTauriInvoke(commands.invoke);

    render(<App />);

    expect(await screen.findByLabelText("Task matrix")).toBeTruthy();
    expect(screen.getByText("Do")).toBeTruthy();
    expect(screen.getByText("Schedule")).toBeTruthy();
    expect(screen.getByText("Delegate")).toBeTruthy();
    expect(screen.getByText("Eliminate")).toBeTruthy();
    expect(screen.getByText("Skipped")).toBeTruthy();
    expect(screen.getByText("Done")).toBeTruthy();
    expect(screen.getByText("Visible")).toBeTruthy();
    expect(screen.queryByText("Hidden")).toBeNull();
    expect(dndKitMock.droppableIds).toContain(areaDropId("skipped"));
    expect(dndKitMock.droppableIds).toContain(areaDropId("done"));
  });

  it("creates task cards through Tauri commands and refreshes the matrix", async () => {
    const commands = new FakeTauriCommands();

    installTauriInvoke(commands.invoke);
    render(<App />);

    await screen.findByLabelText("Task matrix");
    createTaskInArea("Do", "First");
    expect(await screen.findByText("First")).toBeTruthy();

    createTaskInArea("Schedule", "Planned");
    expect(await screen.findByText("Planned")).toBeTruthy();

    expect(taskTitlesIn("Do tasks")).toEqual(["First"]);
    expect(taskTitlesIn("Schedule tasks")).toEqual(["Planned"]);
    expect(screen.getByLabelText("Do task count").textContent).toBe("1 cards");
  });

  it("updates a task title through Tauri commands", async () => {
    const commands = new FakeTauriCommands();

    commands.seed(task({ id: "task-1", title: "Original title", areaId: "do" }));
    installTauriInvoke(commands.invoke);
    render(<App />);

    expect(await screen.findByText("Original title")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Task title"), {
      target: { value: "  Updated title  " }
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Updated title")).toBeTruthy();
    expect(screen.queryByText("Original title")).toBeNull();
    expect(commands.tasks[0]).toMatchObject({ title: "Updated title" });
  });

  it("hides active tasks from the matrix after dropping them on terminal areas", async () => {
    const commands = new FakeTauriCommands();

    commands.seed(task({ id: "task-1", title: "Done task", areaId: "do" }));
    installTauriInvoke(commands.invoke);
    render(<App />);

    expect(await screen.findByText("Done task")).toBeTruthy();
    dragTaskOverArea("task-1", "done");

    await waitFor(() => expect(screen.queryByText("Done task")).toBeNull());
    expect(commands.tasks[0]).toMatchObject({
      areaId: "done",
      status: "done"
    });
  });
});

function installTauriInvoke(invoke: Invoke | undefined) {
  Object.defineProperty(window, "__TAURI_INTERNALS__", {
    configurable: true,
    value: invoke === undefined ? undefined : { invoke }
  });
}

function task(input: Partial<Task> & Pick<Task, "id" | "title">): Task {
  return {
    areaId: "do",
    order: 0,
    status: "active",
    ...input
  };
}

function taskTitlesIn(listName: string): string[] {
  return Array.from(
    screen.getByRole("list", { name: listName }).querySelectorAll(".task-card__title")
  ).map((item) => item.textContent ?? "");
}

function createTaskInArea(areaLabel: string, title: string) {
  fireEvent.change(screen.getByLabelText(`New task title for ${areaLabel}`), {
    target: { value: title }
  });
  fireEvent.click(screen.getByRole("button", { name: `Add task to ${areaLabel}` }));
}

function dragTaskOverArea(taskId: string, areaId: AreaId) {
  dndKitMock.onDragEnd?.({
    active: { id: taskDropId(taskId) },
    over: { id: areaDropId(areaId) }
  });
}

class FakeTauriCommands {
  readonly tasks: Task[] = [];

  private nextId = 1;

  seed(...tasks: Task[]) {
    this.tasks.splice(0, this.tasks.length, ...tasks);
    this.normalizeAllAreas();
  }

  readonly invoke = async <T,>(command: string, args?: InvokeArgs): Promise<T> => {
    switch (command) {
      case "get_storage_health":
        return { ok: true } as T;
      case "list_tasks":
        return this.sortedTasks() as T;
      case "create_task":
        return this.createTask(inputFromArgs<CreateTaskInput>(args)) as T;
      case "move_task":
        return this.moveTask(inputFromArgs<MoveTaskInput>(args)) as T;
      case "reorder_task":
        return this.reorderTask(inputFromArgs<ReorderTaskInput>(args)) as T;
      case "update_task_title":
        return this.updateTaskTitle(inputFromArgs<UpdateTaskTitleInput>(args)) as T;
      default:
        throw new Error(`Unexpected command: ${command}`);
    }
  };

  private createTask(input: CreateTaskInput): Task {
    const task = {
      areaId: input.areaId,
      id: `task-${this.nextId++}`,
      order: this.tasksInArea(input.areaId).length,
      status: "active",
      title: input.title
    } satisfies Task;

    this.tasks.push(task);

    return task;
  }

  private moveTask(input: MoveTaskInput): Task {
    const task = this.findTask(input.taskId);

    this.removeTask(task.id);
    this.normalizeArea(task.areaId);

    const movedTask = {
      ...task,
      areaId: input.toAreaId,
      status: statusForArea(input.toAreaId)
    } satisfies Task;
    const targetTasks = this.tasksInArea(input.toAreaId);
    const insertAt = clamp(input.insertAt ?? targetTasks.length, 0, targetTasks.length);

    targetTasks.splice(insertAt, 0, movedTask);
    this.replaceArea(input.toAreaId, targetTasks);

    return movedTask;
  }

  private reorderTask(input: ReorderTaskInput): Task {
    const task = this.findTask(input.taskId);
    const areaTasks = this.tasksInArea(task.areaId).filter(
      (candidate) => candidate.id !== task.id
    );
    const insertAt = clamp(input.toIndex, 0, areaTasks.length);

    areaTasks.splice(insertAt, 0, task);
    this.replaceArea(task.areaId, areaTasks);

    return this.findTask(input.taskId);
  }

  private updateTaskTitle(input: UpdateTaskTitleInput): Task {
    const task = this.findTask(input.taskId);
    const updatedTask = { ...task, title: input.title } satisfies Task;

    this.tasks[this.tasks.findIndex((candidate) => candidate.id === task.id)] =
      updatedTask;

    return updatedTask;
  }

  private sortedTasks(): Task[] {
    return [...this.tasks].sort(
      (left, right) =>
        AREA_ORDER.indexOf(left.areaId) - AREA_ORDER.indexOf(right.areaId) ||
        left.order - right.order
    );
  }

  private tasksInArea(areaId: AreaId): Task[] {
    return this.tasks
      .filter((task) => task.areaId === areaId)
      .sort((left, right) => left.order - right.order);
  }

  private replaceArea(areaId: AreaId, tasks: Task[]) {
    const otherTasks = this.tasks.filter((task) => task.areaId !== areaId);
    const normalizedTasks = tasks.map((task, order) => ({ ...task, order }));

    this.tasks.splice(0, this.tasks.length, ...otherTasks, ...normalizedTasks);
  }

  private normalizeArea(areaId: AreaId) {
    this.replaceArea(areaId, this.tasksInArea(areaId));
  }

  private normalizeAllAreas() {
    for (const areaId of AREA_ORDER) {
      this.normalizeArea(areaId);
    }
  }

  private findTask(taskId: TaskId): Task {
    const task = this.tasks.find((candidate) => candidate.id === taskId);

    if (task === undefined) {
      throw new Error("Task not found.");
    }

    return task;
  }

  private removeTask(taskId: TaskId) {
    this.tasks.splice(
      this.tasks.findIndex((task) => task.id === taskId),
      1
    );
  }
}

type CreateTaskInput = {
  readonly areaId: MatrixAreaId;
  readonly title: string;
};

type MoveTaskInput = {
  readonly taskId: TaskId;
  readonly toAreaId: AreaId;
  readonly insertAt?: number;
};

type ReorderTaskInput = {
  readonly taskId: TaskId;
  readonly toIndex: number;
};

type UpdateTaskTitleInput = {
  readonly taskId: TaskId;
  readonly title: string;
};

const AREA_ORDER = [
  "do",
  "schedule",
  "delegate",
  "eliminate",
  "skipped",
  "done"
] as const satisfies readonly AreaId[];

function inputFromArgs<T>(args: InvokeArgs | undefined): T {
  if (args === undefined || !("input" in args)) {
    throw new Error("Command input missing.");
  }

  return args.input as T;
}

function statusForArea(areaId: AreaId): TaskStatus {
  if (areaId === "done" || areaId === "skipped") {
    return areaId;
  }

  return "active";
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
