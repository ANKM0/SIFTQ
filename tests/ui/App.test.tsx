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
    expect(commands.calls).toEqual([
      { command: "get_storage_health" },
      { command: "list_tasks" }
    ]);
  });

  it("creates task cards through Tauri commands and refreshes the matrix", async () => {
    const commands = new FakeTauriCommands();

    installTauriInvoke(commands.invoke);
    render(<App />);

    await screen.findByLabelText("Task matrix");
    commands.clearCalls();

    createTaskInArea("Do", "  First  ");
    expect(await screen.findByText("First")).toBeTruthy();
    expect(commands.calls).toEqual([
      {
        command: "create_task",
        args: { input: { areaId: "do", title: "First" } }
      },
      { command: "list_tasks" }
    ]);

    commands.clearCalls();
    createTaskInArea("Schedule", "Planned");
    expect(await screen.findByText("Planned")).toBeTruthy();

    expect(taskTitlesIn("Do tasks")).toEqual(["First"]);
    expect(taskTitlesIn("Schedule tasks")).toEqual(["Planned"]);
    expect(screen.getByLabelText("Do task count").textContent).toBe("1 cards");
    expect(commands.calls).toEqual([
      {
        command: "create_task",
        args: { input: { areaId: "schedule", title: "Planned" } }
      },
      { command: "list_tasks" }
    ]);
  });

  it("updates a task title through Tauri commands", async () => {
    const commands = new FakeTauriCommands();

    commands.seed(task({ id: "task-1", title: "Original title", areaId: "do" }));
    installTauriInvoke(commands.invoke);
    render(<App />);

    expect(await screen.findByText("Original title")).toBeTruthy();
    commands.clearCalls();

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Task title"), {
      target: { value: "  Updated title  " }
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Updated title")).toBeTruthy();
    expect(screen.queryByText("Original title")).toBeNull();
    expect(commands.tasks[0]).toMatchObject({ title: "Updated title" });
    expect(commands.calls).toEqual([
      {
        command: "update_task_title",
        args: { input: { taskId: "task-1", title: "Updated title" } }
      },
      { command: "list_tasks" }
    ]);
  });

  it("reorders and moves task cards through Tauri commands", async () => {
    const commands = new FakeTauriCommands();

    commands.seed(
      task({ id: "task-1", title: "First task", areaId: "do", order: 0 }),
      task({ id: "task-2", title: "Second task", areaId: "do", order: 1 }),
      task({
        id: "task-3",
        title: "Scheduled task",
        areaId: "schedule",
        order: 0
      })
    );
    installTauriInvoke(commands.invoke);
    render(<App />);

    expect(await screen.findByText("First task")).toBeTruthy();
    commands.clearCalls();

    dragTaskOverTask("task-2", "task-1");
    await waitFor(() =>
      expect(taskTitlesIn("Do tasks")).toEqual(["Second task", "First task"])
    );
    expect(commands.calls).toEqual([
      {
        command: "reorder_task",
        args: { input: { taskId: "task-2", toIndex: 0 } }
      },
      { command: "list_tasks" }
    ]);

    commands.clearCalls();
    dragTaskOverTask("task-1", "task-3");
    await waitFor(() =>
      expect(taskTitlesIn("Schedule tasks")).toEqual([
        "First task",
        "Scheduled task"
      ])
    );
    expect(commands.calls).toEqual([
      {
        command: "move_task",
        args: {
          input: { taskId: "task-1", toAreaId: "schedule", insertAt: 0 }
        }
      },
      { command: "list_tasks" }
    ]);
  });

  it.each(["done", "skipped"] as const)(
    "hides active tasks from the matrix after dropping them on the %s area",
    async (terminalAreaId) => {
      const commands = new FakeTauriCommands();

      commands.seed(
        task({ id: "task-1", title: `${terminalAreaId} task`, areaId: "do" })
      );
      installTauriInvoke(commands.invoke);
      render(<App />);

      expect(await screen.findByText(`${terminalAreaId} task`)).toBeTruthy();
      commands.clearCalls();

      dragTaskOverArea("task-1", terminalAreaId);

      await waitFor(() =>
        expect(screen.queryByText(`${terminalAreaId} task`)).toBeNull()
      );
      expect(commands.tasks[0]).toMatchObject({
        areaId: terminalAreaId,
        status: terminalAreaId
      });
      expect(commands.calls).toEqual([
        {
          command: "move_task",
          args: {
            input: { taskId: "task-1", toAreaId: terminalAreaId, insertAt: 0 }
          }
        },
        { command: "list_tasks" }
      ]);
    }
  );
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

function dragTaskOverTask(taskId: string, overTaskId: TaskId) {
  dndKitMock.onDragEnd?.({
    active: { id: taskDropId(taskId) },
    over: { id: taskDropId(overTaskId) }
  });
}

type TauriCall = {
  readonly command: string;
  readonly args?: InvokeArgs;
};

class FakeTauriCommands {
  readonly calls: TauriCall[] = [];
  readonly tasks: Task[] = [];

  private nextId = 1;

  clearCalls() {
    this.calls.splice(0, this.calls.length);
  }

  seed(...tasks: Task[]) {
    this.tasks.splice(0, this.tasks.length, ...tasks);
    this.normalizeAllAreas();
  }

  readonly invoke = async <T,>(command: string, args?: InvokeArgs): Promise<T> => {
    this.calls.push(
      args === undefined
        ? { command }
        : {
            args,
            command
          }
    );

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
