import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { InMemoryTaskRepository } from "../../src/adapters/inMemoryTaskRepository";
import {
  createTask,
  moveTask,
  reorderTask
} from "../../src/application/taskOperations";
import { App } from "../../src/ui/App";

afterEach(() => {
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
    expect(screen.getByText("First").className).toContain("task-card");
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
    screen.getByRole("list", { name: listName }).querySelectorAll(".task-card")
  ).map((item) => item.textContent ?? "");
}

function createTaskInArea(areaLabel: string, title: string) {
  fireEvent.change(screen.getByLabelText(`New task title for ${areaLabel}`), {
    target: { value: title }
  });
  fireEvent.click(screen.getByRole("button", { name: `Add task to ${areaLabel}` }));
}
