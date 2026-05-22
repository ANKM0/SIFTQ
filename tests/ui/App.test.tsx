import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InMemoryTaskRepository } from "../../src/adapters/inMemoryTaskRepository";
import {
  createTask,
  moveTask,
  reorderTask
} from "../../src/application/taskOperations";
import { type AreaId } from "../../src/domain/area";
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
  cleanup();
});

describe("App", () => {
  it("renders the matrix quadrants", () => {
    render(<App />);

    expect(screen.getByLabelText("Task matrix").className).toContain("matrix-grid");
    expect(screen.getByText("Do")).toBeTruthy();
    expect(screen.getByText("Schedule")).toBeTruthy();
    expect(screen.getByText("Delegate")).toBeTruthy();
    expect(screen.getByText("Eliminate")).toBeTruthy();
  });

  it("renders the terminal drop areas", () => {
    render(<App />);

    expect(screen.getByText("Skipped")).toBeTruthy();
    expect(screen.getByText("Done")).toBeTruthy();
    expect(dndKitMock.droppableIds).toContain(areaDropId("skipped"));
    expect(dndKitMock.droppableIds).toContain(areaDropId("done"));
  });

  it("renders area panels with card counts and task card regions", () => {
    render(<App />);

    expect(screen.getByLabelText("Do task count").textContent).toBe("0 cards");
    expect(screen.getByLabelText("Schedule task count").textContent).toBe("0 cards");
    expect(screen.getByLabelText("Delegate task count").textContent).toBe("0 cards");
    expect(screen.getByLabelText("Eliminate task count").textContent).toBe("0 cards");
    expect(screen.getByRole("list", { name: "Do tasks" }).className).toContain(
      "area-panel__tasks"
    );
    expect(screen.getByRole("list", { name: "Do tasks" }).textContent).toBe(
      "No cards"
    );
  });

  it("marks empty areas as visible drop regions", () => {
    render(<App />);

    expect(screen.getByText("Do").closest("article")?.className).toContain(
      "area-panel--empty"
    );
    expect(screen.getAllByText("No cards")).toHaveLength(4);
  });

  it("creates task cards in the selected matrix area", async () => {
    const repository = new InMemoryTaskRepository();

    render(<App repository={repository} />);

    createTaskInArea("Do", "First");
    expect(await screen.findByText("First")).toBeTruthy();

    createTaskInArea("Schedule", "Planned");
    expect(await screen.findByText("Planned")).toBeTruthy();

    createTaskInArea("Do", "Second");
    expect(await screen.findByText("Second")).toBeTruthy();

    expect(taskTitlesIn("Do tasks")).toEqual(["First", "Second"]);
    expect(taskTitlesIn("Schedule tasks")).toEqual(["Planned"]);
    expect(screen.getByLabelText("Do task count").textContent).toBe("2 cards");
    expect(screen.getByText("First").closest(".task-card")).toBeTruthy();
    expect(
      screen.getAllByRole("button", { name: "Edit" })[0]?.closest(".task-card")
    ).toBeTruthy();
  });

  it("keeps each area form independent while updating area-specific card lists", async () => {
    render(<App repository={new InMemoryTaskRepository()} />);

    fireEvent.change(screen.getByLabelText("New task title for Do"), {
      target: { value: "Do draft" }
    });
    fireEvent.change(screen.getByLabelText("New task title for Delegate"), {
      target: { value: "Delegated" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Add task to Delegate" }));

    expect(await screen.findByText("Delegated")).toBeTruthy();
    expect(taskTitlesIn("Do tasks")).toEqual([]);
    expect(taskTitlesIn("Delegate tasks")).toEqual(["Delegated"]);
    expect(screen.getByLabelText("New task title for Do")).toHaveProperty(
      "value",
      "Do draft"
    );
    expect(screen.getByLabelText("Delegate task count").textContent).toBe("1 cards");
  });

  it("keeps created tasks in the same in-memory repository session", async () => {
    const repository = new InMemoryTaskRepository();
    const firstRender = render(<App repository={repository} />);

    createTaskInArea("Do", "Session task");
    expect(await screen.findByText("Session task")).toBeTruthy();

    firstRender.unmount();
    render(<App repository={repository} />);

    expect(await screen.findByText("Session task")).toBeTruthy();
    expect(taskTitlesIn("Do tasks")).toEqual(["Session task"]);
  });

  it("disables creation while the title is blank or too long without truncating input", () => {
    render(<App repository={new InMemoryTaskRepository()} />);

    const input = screen.getByLabelText("New task title for Do");
    const button = screen.getByRole("button", { name: "Add task to Do" });

    expect(button).toHaveProperty("disabled", true);

    fireEvent.change(input, { target: { value: "   " } });
    expect(button).toHaveProperty("disabled", true);

    fireEvent.change(input, { target: { value: "a".repeat(257) } });
    expect(button).toHaveProperty("disabled", true);
    expect(input).toHaveProperty("value", "a".repeat(257));
    expect(screen.getByRole("alert").textContent).toBe(
      "Title must be 256 characters or less."
    );
  });

  it("shows an error if invalid creation is submitted and does not create a card", async () => {
    render(<App repository={new InMemoryTaskRepository()} />);

    fireEvent.submit(screen.getByRole("form", { name: "Create task in Do" }));

    expect((await screen.findByRole("alert")).textContent).toBe(
      "Task title must not be empty."
    );
    expect(taskTitlesIn("Do tasks")).toEqual([]);
  });

  it("allows duplicate titles and clears the input after successful creation", async () => {
    render(<App repository={new InMemoryTaskRepository()} />);

    createTaskInArea("Do", "Duplicate");
    expect(await screen.findByText("Duplicate")).toBeTruthy();

    createTaskInArea("Do", "Duplicate");

    await waitFor(() =>
      expect(taskTitlesIn("Do tasks")).toEqual(["Duplicate", "Duplicate"])
    );
    expect(screen.getByLabelText("New task title for Do")).toHaveProperty(
      "value",
      ""
    );
  });

  it("opens the title edit modal from a task card and saves an updated title", async () => {
    const repository = new InMemoryTaskRepository();

    await createTask(repository, { areaId: "do", title: "Original title" });

    render(<App repository={repository} />);

    expect(await screen.findByText("Original title")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));

    expect(screen.getByRole("dialog", { name: "Edit task title" })).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Task title"), {
      target: { value: "  Updated title  " }
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Updated title")).toBeTruthy();
    expect(screen.queryByText("Original title")).toBeNull();
    expect(screen.queryByRole("dialog", { name: "Edit task title" })).toBeNull();
    expect((await repository.listTasks())[0]).toMatchObject({
      title: "Updated title",
      areaId: "do",
      status: "active",
      order: 0
    });
  });

  it("closes the title edit modal on cancel without changing the task", async () => {
    const repository = new InMemoryTaskRepository();

    await createTask(repository, { areaId: "do", title: "Original title" });

    render(<App repository={repository} />);

    expect(await screen.findByText("Original title")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Task title"), {
      target: { value: "Draft title" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("dialog", { name: "Edit task title" })).toBeNull();
    expect(screen.getByText("Original title")).toBeTruthy();
    expect((await repository.listTasks())[0]?.title).toBe("Original title");
  });

  it("disables title update save while the title is blank or too long", async () => {
    const repository = new InMemoryTaskRepository();

    await createTask(repository, { areaId: "do", title: "Original title" });

    render(<App repository={repository} />);

    expect(await screen.findByText("Original title")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));

    const input = screen.getByLabelText("Task title");
    const saveButton = screen.getByRole("button", { name: "Save" });

    fireEvent.change(input, { target: { value: "   " } });

    expect(saveButton).toHaveProperty("disabled", true);
    expect(screen.getByRole("alert").textContent).toBe(
      "Task title must not be empty."
    );

    fireEvent.change(input, { target: { value: "a".repeat(257) } });

    expect(saveButton).toHaveProperty("disabled", true);
    expect(input).toHaveProperty("value", "a".repeat(257));
    expect(screen.getByRole("alert").textContent).toBe(
      "Title must be 256 characters or less."
    );
    expect((await repository.listTasks())[0]?.title).toBe("Original title");
  });

  it("allows duplicate titles when editing a task", async () => {
    const repository = new InMemoryTaskRepository();

    await createTask(repository, { areaId: "do", title: "Duplicate" });
    await createTask(repository, { areaId: "do", title: "Unique" });

    render(<App repository={repository} />);

    expect(await screen.findByText("Unique")).toBeTruthy();

    fireEvent.click(screen.getAllByRole("button", { name: "Edit" })[1]!);
    fireEvent.change(screen.getByLabelText("Task title"), {
      target: { value: "Duplicate" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(taskTitlesIn("Do tasks")).toEqual(["Duplicate", "Duplicate"])
    );
  });

  it("renders task cards in repository order after reordering", async () => {
    const repository = new InMemoryTaskRepository();
    const firstTask = await createTask(repository, { areaId: "do", title: "First" });
    const secondTask = await createTask(repository, { areaId: "do", title: "Second" });
    const thirdTask = await createTask(repository, { areaId: "do", title: "Third" });

    await reorderTask(repository, { taskId: thirdTask.id, toIndex: 0 });

    render(<App repository={repository} />);

    expect(await screen.findByText("Third")).toBeTruthy();
    expect(taskTitlesIn("Do tasks")).toEqual(["Third", "First", "Second"]);
    expect(firstTask.id).not.toBe(secondTask.id);
  });

  it("renders task cards in repository order after moving between areas", async () => {
    const repository = new InMemoryTaskRepository();
    const movedTask = await createTask(repository, { areaId: "do", title: "Moved" });

    await createTask(repository, { areaId: "schedule", title: "Top" });
    await createTask(repository, { areaId: "schedule", title: "Bottom" });
    await moveTask(repository, {
      taskId: movedTask.id,
      toAreaId: "schedule",
      insertAt: 1
    });

    render(<App repository={repository} />);

    expect(await screen.findByText("Moved")).toBeTruthy();
    expect(taskTitlesIn("Schedule tasks")).toEqual(["Top", "Moved", "Bottom"]);
  });

  it("does not render terminal tasks in matrix task lists", async () => {
    const repository = new InMemoryTaskRepository();
    const task = await createTask(repository, { areaId: "do", title: "Done task" });

    await moveTask(repository, { taskId: task.id, toAreaId: "done" });

    render(<App repository={repository} />);

    expect(screen.queryByText("Done task")).toBeNull();
    expect(taskTitlesIn("Do tasks")).toEqual([]);
  });

  it.each([
    ["Done", "done"],
    ["Skipped", "skipped"]
  ] as const)(
    "hides active tasks from the matrix after dropping them on %s",
    async (_label, terminalAreaId) => {
      const repository = new InMemoryTaskRepository();
      const task = await createTask(repository, {
        areaId: "do",
        title: `${terminalAreaId} task`
      });

      render(<App repository={repository} />);

      expect(await screen.findByText(`${terminalAreaId} task`)).toBeTruthy();

      dragTaskOverArea(task.id, terminalAreaId);

      await waitFor(() =>
        expect(screen.queryByText(`${terminalAreaId} task`)).toBeNull()
      );

      const [updatedTask] = await repository.listTasks();
      expect(updatedTask).toMatchObject({
        areaId: terminalAreaId,
        status: terminalAreaId
      });
      expect(taskTitlesIn("Do tasks")).toEqual([]);
      expect(screen.queryByRole("list", { name: `${_label} tasks` })).toBeNull();
    }
  );

  it("renders maximum length task titles in a wrapping card", async () => {
    const repository = new InMemoryTaskRepository();
    const longTitle = "a".repeat(256);

    await createTask(repository, { areaId: "do", title: longTitle });

    render(<App repository={repository} />);

    const card = await screen.findByText(longTitle);

    expect(card.className).toContain("task-card");
    expect(card.textContent).toHaveLength(256);
  });
});

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
