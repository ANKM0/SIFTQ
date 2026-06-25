import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BROWSER_TASK_STORAGE_KEY } from "../../src/adapters/browserTaskRepository";
import {
  type AreaId,
  type Task,
  type TaskId
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

beforeEach(() => {
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: new MemoryStorage()
  });
  window.localStorage.clear();
});

afterEach(() => {
  dndKitMock.droppableIds = [];
  dndKitMock.onDragEnd = undefined;
  cleanup();
});

describe("App", () => {
  it("renders the matrix quadrants and terminal drop areas in a browser", async () => {
    seedStoredTasks(
      task({ id: "task-1", title: "Visible", areaId: "do" }),
      task({ id: "task-2", title: "Hidden", areaId: "done", status: "done" })
    );

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

  it("renders a storage error when browser storage is corrupt", async () => {
    window.localStorage.setItem(BROWSER_TASK_STORAGE_KEY, "{");

    render(<App />);

    expect(await screen.findByText("Storage error")).toBeTruthy();
    expect(screen.getByText("STORAGE")).toBeTruthy();
  });

  it("creates task cards in browser storage and refreshes the matrix", async () => {
    render(<App />);

    await screen.findByLabelText("Task matrix");

    createTaskInArea("Do", "  First  ");
    expect(await screen.findByText("First")).toBeTruthy();

    createTaskInArea("Schedule", "Planned");
    expect(await screen.findByText("Planned")).toBeTruthy();

    expect(taskTitlesIn("Do tasks")).toEqual(["First"]);
    expect(taskTitlesIn("Schedule tasks")).toEqual(["Planned"]);
    expect(screen.getByLabelText("Do task count").textContent).toBe("1 cards");
    expect(storedTasks().map((storedTask) => storedTask.title)).toEqual([
      "First",
      "Planned"
    ]);
  });

  it("updates a task title in browser storage", async () => {
    seedStoredTasks(task({ id: "task-1", title: "Original title", areaId: "do" }));
    render(<App />);

    expect(await screen.findByText("Original title")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Task title"), {
      target: { value: "  Updated title  " }
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Updated title")).toBeTruthy();
    expect(screen.queryByText("Original title")).toBeNull();
    expect(storedTasks()[0]).toMatchObject({ title: "Updated title" });
  });

  it("reorders and moves task cards in browser storage", async () => {
    seedStoredTasks(
      task({ id: "task-1", title: "First task", areaId: "do", order: 0 }),
      task({ id: "task-2", title: "Second task", areaId: "do", order: 1 }),
      task({
        id: "task-3",
        title: "Scheduled task",
        areaId: "schedule",
        order: 0
      })
    );
    render(<App />);

    expect(await screen.findByText("First task")).toBeTruthy();

    dragTaskOverTask("task-2", "task-1");
    await waitFor(() =>
      expect(taskTitlesIn("Do tasks")).toEqual(["Second task", "First task"])
    );

    dragTaskOverTask("task-1", "task-3");
    await waitFor(() =>
      expect(taskTitlesIn("Schedule tasks")).toEqual([
        "First task",
        "Scheduled task"
      ])
    );
    expect(storedTasks()).toMatchObject([
      {
        id: "task-2",
        title: "Second task",
        areaId: "do",
        order: 0,
        listOrder: 1,
        status: "active"
      },
      {
        id: "task-1",
        title: "First task",
        areaId: "schedule",
        order: 0,
        listOrder: 0,
        status: "active"
      },
      {
        id: "task-3",
        title: "Scheduled task",
        areaId: "schedule",
        order: 1,
        listOrder: 2,
        status: "active"
      }
    ]);
  });

  it.each(["done", "skipped"] as const)(
    "hides active tasks from the matrix after dropping them on the %s area",
    async (terminalAreaId) => {
      seedStoredTasks(
        task({ id: "task-1", title: `${terminalAreaId} task`, areaId: "do" })
      );
      render(<App />);

      expect(await screen.findByText(`${terminalAreaId} task`)).toBeTruthy();

      dragTaskOverArea("task-1", terminalAreaId);

      await waitFor(() =>
        expect(screen.queryByText(`${terminalAreaId} task`)).toBeNull()
      );
      expect(storedTasks()[0]).toMatchObject({
        areaId: terminalAreaId,
        status: terminalAreaId
      });
    }
  );

  it("restores task title, area, status, and order after browser reload", async () => {
    seedStoredTasks(
      task({ id: "task-1", title: "First task", areaId: "schedule", order: 1 }),
      task({ id: "task-2", title: "Top task", areaId: "schedule", order: 0 }),
      task({ id: "task-3", title: "Done task", areaId: "done", status: "done" })
    );

    const firstRender = render(<App />);

    expect(await screen.findByText("Top task")).toBeTruthy();
    expect(taskTitlesIn("Schedule tasks")).toEqual(["Top task", "First task"]);
    expect(screen.queryByText("Done task")).toBeNull();

    firstRender.unmount();
    render(<App />);

    expect(await screen.findByText("Top task")).toBeTruthy();
    expect(taskTitlesIn("Schedule tasks")).toEqual(["Top task", "First task"]);
    expect(screen.queryByText("Done task")).toBeNull();
  });
});

function seedStoredTasks(...tasks: Task[]) {
  window.localStorage.setItem(
    BROWSER_TASK_STORAGE_KEY,
    JSON.stringify({
      tasks: tasks.map((task, listOrder) => ({ ...task, listOrder })),
      version: 1
    })
  );
}

function storedTasks(): Task[] {
  const store = JSON.parse(
    window.localStorage.getItem(BROWSER_TASK_STORAGE_KEY) ?? "{\"tasks\":[]}"
  ) as { tasks: Task[] };

  return store.tasks;
}

class MemoryStorage implements Pick<Storage, "clear" | "getItem" | "setItem"> {
  private readonly items = new Map<string, string>();

  clear(): void {
    this.items.clear();
  }

  getItem(key: string): string | null {
    return this.items.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.items.set(key, value);
  }
}

function task(input: Partial<Task> & Pick<Task, "id" | "title">): Task {
  const areaId = input.areaId ?? "do";

  return {
    areaId,
    createdAt: new Date(0).toISOString(),
    description: "",
    listOrder: input.order ?? 0,
    order: 0,
    status: areaId === "done" ? "done" : areaId === "skipped" ? "skipped" : "active",
    updatedAt: new Date(0).toISOString(),
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
