import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  BROWSER_TASK_STORAGE_KEY,
  browserTaskRepository
} from "../../src/adapters/browserTaskRepository";
import {
  type AreaId,
  type Task,
  type TaskId
} from "../../src/contracts/task";
import { App } from "../../src/ui/App";
import {
  areaDropId,
  matrixCollisionDetection,
  taskDropId
} from "../../src/ui/dragDrop";

const dndKitMock = vi.hoisted(() => ({
  collisionDetection: undefined as unknown,
  droppableIds: [] as string[],
  droppableNodes: new Map<string, HTMLElement | null>(),
  overIds: new Set<string>(),
  onDragEnd: undefined as ((event: unknown) => void) | undefined
}));

vi.mock("@dnd-kit/core", async () => {
  const React = await vi.importActual<typeof import("react")>("react");

  return {
    DndContext: ({
      children,
      collisionDetection,
      onDragEnd
    }: {
      children: React.ReactNode;
      collisionDetection?: unknown;
      onDragEnd: (event: unknown) => void;
    }) => {
      dndKitMock.collisionDetection = collisionDetection;
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
        isOver: dndKitMock.overIds.has(id),
        setNodeRef: vi.fn((node: HTMLElement | null) => {
          dndKitMock.droppableNodes.set(id, node);
        })
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
  window.location.hash = "";
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

afterEach(() => {
  dndKitMock.collisionDetection = undefined;
  dndKitMock.droppableIds = [];
  dndKitMock.droppableNodes = new Map();
  dndKitMock.overIds = new Set();
  dndKitMock.onDragEnd = undefined;
  vi.restoreAllMocks();
  cleanup();
});

describe("App", () => {
  it("renders the matrix quadrants and terminal drop areas in a browser", async () => {
    seedStoredTasks(
      task({
        id: "task-1",
        title: "Visible",
        areaId: "do",
        createdAt: "2024-01-02T03:04:05.000Z",
        updatedAt: "2024-01-03T03:04:05.000Z"
      }),
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
    expect(screen.queryByText("2024-01-02T03:04:05.000Z")).toBeNull();
    expect(screen.queryByText("2024-01-03T03:04:05.000Z")).toBeNull();
    expect(screen.queryByText("作成日時")).toBeNull();
    expect(screen.queryByText("更新日時")).toBeNull();
    expect(dndKitMock.droppableIds).toContain(areaDropId("skipped"));
    expect(dndKitMock.droppableIds).toContain(areaDropId("done"));
  });

  it("registers terminal droppables in the same area namespace as matrix areas", async () => {
    seedStoredTasks(
      task({ id: "task-1", title: "Do task", areaId: "do" }),
      task({ id: "task-2", title: "Schedule task", areaId: "schedule" })
    );

    render(<App />);

    expect(await screen.findByLabelText("Task matrix")).toBeTruthy();
    expect(dndKitMock.droppableIds).toEqual([
      areaDropId("skipped"),
      areaDropId("do"),
      taskDropId("task-1"),
      areaDropId("schedule"),
      taskDropId("task-2"),
      areaDropId("delegate"),
      areaDropId("eliminate"),
      areaDropId("done")
    ]);
  });

  it("attaches terminal droppable refs to the visible full-height side-column shells", async () => {
    render(<App />);

    expect(await screen.findByLabelText("Task matrix")).toBeTruthy();

    const skippedNode = dndKitMock.droppableNodes.get(areaDropId("skipped"));
    const doneNode = dndKitMock.droppableNodes.get(areaDropId("done"));
    const skippedHeading = screen.getByRole("heading", { name: "Skipped" });
    const doneHeading = screen.getByRole("heading", { name: "Done" });

    expect(skippedNode?.className).toContain("matrix-workspace__status");
    expect(skippedNode?.className).toContain("matrix-workspace__status--skipped");
    expect(skippedNode?.className).toContain("status-drop-area-shell");
    expect(skippedNode?.childElementCount).toBe(1);
    expect(skippedNode?.firstElementChild?.className).toContain("status-drop-area");
    expect(skippedHeading.closest(".status-drop-area-shell")).toBe(skippedNode);
    expect(doneNode?.className).toContain("matrix-workspace__status");
    expect(doneNode?.className).toContain("matrix-workspace__status--done");
    expect(doneNode?.className).toContain("status-drop-area-shell");
    expect(doneNode?.childElementCount).toBe(1);
    expect(doneNode?.firstElementChild?.className).toContain("status-drop-area");
    expect(doneHeading.closest(".status-drop-area-shell")).toBe(doneNode);
  });

  it("keeps the skipped-board-done DOM order used by the mobile vertical stack", async () => {
    render(<App />);

    const workspace = await screen.findByLabelText("Matrix workspace");
    const childClassNames = Array.from(workspace?.children ?? []).map((child) => child.className);

    expect(workspace).toBeTruthy();
    expect(childClassNames).toHaveLength(3);
    expect(childClassNames[0]).toContain("matrix-workspace__status--skipped");
    expect(childClassNames[1]).toBe("matrix-grid");
    expect(childClassNames[2]).toContain("matrix-workspace__status--done");
  });

  it.each(["done", "skipped"] as const)(
    "highlights only the %s terminal shell when its drop target is active",
    async (terminalAreaId) => {
      dndKitMock.overIds = new Set([areaDropId(terminalAreaId)]);

      render(<App />);

      expect(await screen.findByLabelText("Task matrix")).toBeTruthy();

      const activeShell = dndKitMock.droppableNodes.get(areaDropId(terminalAreaId));
      const inactiveAreaId = terminalAreaId === "done" ? "skipped" : "done";
      const inactiveShell = dndKitMock.droppableNodes.get(areaDropId(inactiveAreaId));

      expect(activeShell?.className).toContain("status-drop-area-shell--drop-target");
      expect(activeShell?.firstElementChild?.className).toContain(
        "status-drop-area--drop-target"
      );
      expect(inactiveShell?.className).not.toContain("status-drop-area-shell--drop-target");
      expect(inactiveShell?.firstElementChild?.className).not.toContain(
        "status-drop-area--drop-target"
      );
    }
  );

  it("uses the custom matrix collision ranking on the matrix page", async () => {
    render(<App />);

    expect(await screen.findByLabelText("Task matrix")).toBeTruthy();
    expect(dndKitMock.collisionDetection).toBe(matrixCollisionDetection);
  });

  it("routes to the task list page from #/tasks and shows mutual header links", async () => {
    seedStoredTasks(
      task({
        id: "task-1",
        title: "Visible",
        areaId: "do",
        createdAt: "2024-01-02T03:04:05.000Z",
        description: "This description should stay visible in the list."
      }),
      task({ id: "task-2", title: "Hidden", areaId: "done", status: "done" })
    );
    window.location.hash = "#/tasks";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "マトリックス" }).getAttribute("href")).toBe(
      "#/"
    );
    expect(screen.getByRole("link", { name: "タスク一覧" }).getAttribute("href")).toBe(
      "#/tasks"
    );
    expect(screen.getAllByRole("button", { name: "Do のドラッグハンドル" })).toHaveLength(2);
    expect(screen.getAllByRole("checkbox")).toHaveLength(2);
    expect(screen.getByText("Visible")).toBeTruthy();
    expect(screen.getByText("Hidden")).toBeTruthy();
    expect(screen.getByText("説明なし")).toBeTruthy();
    expect(screen.getByLabelText("現在の選択件数").textContent).toBe("0件選択中");
    expect(screen.getByRole("button", { name: "選択したタスクを削除" })).toHaveProperty(
      "disabled",
      true
    );
    expect(screen.getAllByRole("button", { name: "削除" })).toHaveLength(2);
    expect(screen.queryByText("2024-01-02T03:04:05.000Z")).toBeNull();
    expect(screen.queryByText("作成日時")).toBeNull();
    expect(screen.queryByText("更新日時")).toBeNull();
    expect(screen.queryByLabelText("Task matrix")).toBeNull();
  });

  it("tracks selected tasks from the task list checkboxes", async () => {
    seedStoredTasks(
      task({ id: "task-1", title: "Visible", areaId: "do" }),
      task({ id: "task-2", title: "Hidden", areaId: "done", status: "done" })
    );
    window.location.hash = "#/tasks";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();

    const bulkDeleteButton = screen.getByRole("button", { name: "選択したタスクを削除" });
    const firstCheckbox = screen.getByRole("checkbox", { name: "Visible を選択" });
    const secondCheckbox = screen.getByRole("checkbox", { name: "Hidden を選択" });
    const selectionCount = screen.getByLabelText("現在の選択件数");

    fireEvent.click(firstCheckbox);

    expect(selectionCount.textContent).toBe("1件選択中");
    expect(bulkDeleteButton).toHaveProperty("disabled", false);
    expect(firstCheckbox).toHaveProperty("checked", true);
    expect(secondCheckbox).toHaveProperty("checked", false);
    expect(screen.getByText("選択中")).toBeTruthy();

    fireEvent.click(secondCheckbox);

    expect(selectionCount.textContent).toBe("2件選択中");
    expect(secondCheckbox).toHaveProperty("checked", true);
    expect(screen.getAllByText("選択中")).toHaveLength(2);

    fireEvent.click(firstCheckbox);

    expect(selectionCount.textContent).toBe("1件選択中");
    expect(firstCheckbox).toHaveProperty("checked", false);
    expect(secondCheckbox).toHaveProperty("checked", true);

    fireEvent.click(secondCheckbox);

    expect(selectionCount.textContent).toBe("0件選択中");
    expect(secondCheckbox).toHaveProperty("checked", false);
    expect(bulkDeleteButton).toHaveProperty("disabled", true);
    expect(screen.queryByText("選択中")).toBeNull();
  });

  it("routes to the task detail page from #/tasks/:taskId", async () => {
    seedStoredTasks(task({ id: "task-1", title: "Visible", areaId: "do" }));
    window.location.hash = "#/tasks/task-1";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク詳細" })).toBeTruthy();
    expect(screen.getByDisplayValue("Visible")).toBeTruthy();
    expect((screen.getByLabelText("area") as HTMLSelectElement).value).toBe("do");
    expect((screen.getByLabelText("status") as HTMLSelectElement).value).toBe("active");
    expect(screen.getByText("作成日時")).toBeTruthy();
    expect(screen.getByText("更新日時")).toBeTruthy();
    expect(screen.getByRole("link", { name: "タスク一覧へ戻る" }).getAttribute("href")).toBe(
      "#/tasks"
    );
  });

  it("normalizes legacy terminal tasks to the fallback matrix area in detail", async () => {
    seedStoredTasks(task({ id: "task-1", title: "Finished", areaId: "done", status: "done" }));
    window.location.hash = "#/tasks/task-1";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク詳細" })).toBeTruthy();
    expect((screen.getByLabelText("area") as HTMLSelectElement).value).toBe("do");

    fireEvent.change(screen.getByLabelText("title"), {
      target: { value: "Finished updated" }
    });
    fireEvent.click(screen.getByRole("button", { name: "保存" }));

    await waitFor(() =>
      expect(storedTasks()[0]).toMatchObject({
        areaId: "do",
        status: "done",
        title: "Finished updated"
      })
    );
  });

  it("updates task details from the task detail page", async () => {
    seedStoredTasks(task({ id: "task-1", title: "Visible", areaId: "do" }));
    window.location.hash = "#/tasks/task-1";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク詳細" })).toBeTruthy();

    fireEvent.change(screen.getByLabelText("title"), {
      target: { value: "  Updated task  " }
    });
    fireEvent.change(screen.getByLabelText("description"), {
      target: { value: "Detail view edits the full description text." }
    });
    fireEvent.change(screen.getByLabelText("area"), {
      target: { value: "delegate" }
    });
    fireEvent.change(screen.getByLabelText("status"), {
      target: { value: "done" }
    });
    fireEvent.click(screen.getByRole("button", { name: "保存" }));

    await waitFor(() =>
      expect(storedTasks()[0]).toMatchObject({
        title: "Updated task",
        description: "Detail view edits the full description text.",
        areaId: "delegate",
        status: "done"
      })
    );
    expect(screen.getByDisplayValue("Updated task")).toBeTruthy();
    expect((screen.getByLabelText("area") as HTMLSelectElement).value).toBe("delegate");
    expect((screen.getByLabelText("status") as HTMLSelectElement).value).toBe("done");
  });

  it("deletes a task from the detail page and returns to the task list", async () => {
    seedStoredTasks(task({ id: "task-1", title: "Visible", areaId: "do" }));
    window.location.hash = "#/tasks/task-1";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク詳細" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "削除" }));

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "タスク一覧" })).toBeTruthy()
    );
    expect(window.confirm).toHaveBeenCalledWith('"Visible" を削除しますか?');
    expect(screen.getByRole("status").textContent).toContain("タスクを削除しました");
    expect(storedTasks()).toHaveLength(0);
    expect(window.location.hash).toBe("#/tasks");
  });

  it("stays on the detail page when deleting a task fails", async () => {
    seedStoredTasks(task({ id: "task-1", title: "Visible", areaId: "do" }));
    window.location.hash = "#/tasks/task-1";
    vi.spyOn(browserTaskRepository, "deleteTask").mockRejectedValueOnce(new Error("boom"));

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク詳細" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "削除" }));

    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("boom"));
    expect(screen.getByRole("heading", { name: "タスク詳細" })).toBeTruthy();
    expect(window.location.hash).toBe("#/tasks/task-1");
    expect(storedTasks()).toHaveLength(1);
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("renders a not-found state for a missing detail task", async () => {
    window.location.hash = "#/tasks/missing-task";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスクが見つかりませんでした" })).toBeTruthy();
    expect(screen.getByText("指定された taskId は存在しないか、すでに削除されています。")).toBeTruthy();
    expect(screen.getByRole("link", { name: "タスク一覧へ戻る" }).getAttribute("href")).toBe(
      "#/tasks"
    );
  });

  it("reorders task cards from the task list page", async () => {
    seedStoredTasks(
      task({ id: "task-1", title: "First", areaId: "do", order: 0 }),
      task({ id: "task-2", title: "Second", areaId: "done", status: "done", order: 1 }),
      task({ id: "task-3", title: "Third", areaId: "delegate", order: 0 })
    );
    window.location.hash = "#/tasks";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();

    dragTaskOverTask("task-3", "task-1");

    await waitFor(() => expect(taskListTitles()).toEqual(["Third", "First", "Second"]));
    expect(storedTasks()).toMatchObject([
      { id: "task-3", areaId: "delegate", order: 0, listOrder: 0 },
      { id: "task-1", areaId: "do", order: 0, listOrder: 1 },
      { id: "task-2", areaId: "do", order: 1, listOrder: 2 }
    ]);
  });

  it("updates task status from the task list status menu", async () => {
    seedStoredTasks(task({ id: "task-1", title: "Visible", areaId: "do" }));
    window.location.hash = "#/tasks";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "active" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "done" }));

    await waitFor(() =>
      expect(storedTasks()[0]).toMatchObject({ areaId: "do", status: "done" })
    );
    expect(screen.getByRole("button", { name: "done" })).toBeTruthy();
  });

  it("restores a task to its preserved matrix area when returning it to active", async () => {
    seedStoredTasks(task({ id: "task-1", title: "Visible", areaId: "do" }));
    window.location.hash = "#/tasks";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "active" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "done" }));
    await waitFor(() =>
      expect(storedTasks()[0]).toMatchObject({ areaId: "do", status: "done" })
    );

    fireEvent.click(screen.getByRole("button", { name: "done" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "active" }));
    await waitFor(() =>
      expect(storedTasks()[0]).toMatchObject({ areaId: "do", status: "active" })
    );

    fireEvent.click(screen.getByRole("link", { name: "マトリックス" }));

    expect(await screen.findByLabelText("Task matrix")).toBeTruthy();
    expect(taskTitlesIn("Do tasks")).toEqual(["Visible"]);
  });

  it("shows the full status menu for migrated legacy terminal tasks in the task list", async () => {
    seedStoredTasks(task({ id: "task-1", title: "Finished", areaId: "done", status: "done" }));
    window.location.hash = "#/tasks";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "done" }));

    expect(screen.getByRole("menuitem", { name: "active" })).toBeTruthy();
    expect(screen.getByRole("menuitem", { name: "done" })).toBeTruthy();
    expect(screen.getByRole("menuitem", { name: "skipped" })).toBeTruthy();
  });

  it("deletes a task from the task list and shows a notice", async () => {
    seedStoredTasks(
      task({ id: "task-1", title: "Visible", areaId: "do" }),
      task({ id: "task-2", title: "Hidden", areaId: "done", status: "done" })
    );
    window.location.hash = "#/tasks";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();

    fireEvent.click(screen.getAllByRole("button", { name: "削除" })[0]);

    await waitFor(() =>
      expect(screen.getByRole("status").textContent).toContain("タスクを削除しました")
    );
    expect(window.confirm).toHaveBeenCalledWith('"Visible" を削除しますか?');
    expect(taskListTitles()).toEqual(["Hidden"]);
  });

  it("removes a deleted active task from the matrix after leaving the task list", async () => {
    seedStoredTasks(
      task({ id: "task-1", title: "Visible", areaId: "do" }),
      task({ id: "task-2", title: "Scheduled", areaId: "schedule" })
    );
    window.location.hash = "#/tasks";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();

    fireEvent.click(screen.getAllByRole("button", { name: "削除" })[0]);

    await waitFor(() =>
      expect(screen.getByRole("status").textContent).toContain("タスクを削除しました")
    );

    fireEvent.click(screen.getByRole("link", { name: "マトリックス" }));

    expect(await screen.findByLabelText("Task matrix")).toBeTruthy();
    expect(screen.queryByText("Visible")).toBeNull();
    expect(taskTitlesIn("Schedule tasks")).toEqual(["Scheduled"]);
  });

  it("drops removed tasks from the local selection state", async () => {
    seedStoredTasks(
      task({ id: "task-1", title: "Visible", areaId: "do" }),
      task({ id: "task-2", title: "Hidden", areaId: "done", status: "done" })
    );
    window.location.hash = "#/tasks";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();

    fireEvent.click(screen.getByRole("checkbox", { name: "Visible を選択" }));
    expect(screen.getByLabelText("現在の選択件数").textContent).toBe("1件選択中");

    fireEvent.click(screen.getAllByRole("button", { name: "削除" })[0]);

    await waitFor(() =>
      expect(screen.getByLabelText("現在の選択件数").textContent).toBe("0件選択中")
    );
    expect(screen.getByRole("button", { name: "選択したタスクを削除" })).toHaveProperty(
      "disabled",
      true
    );
    expect(screen.queryByRole("checkbox", { name: "Visible を選択" })).toBeNull();
  });

  it("keeps the task list unchanged when delete confirmation is canceled", async () => {
    seedStoredTasks(
      task({ id: "task-1", title: "Visible", areaId: "do" }),
      task({ id: "task-2", title: "Hidden", areaId: "done", status: "done" })
    );
    window.location.hash = "#/tasks";
    vi.mocked(window.confirm).mockReturnValueOnce(false);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();

    fireEvent.click(screen.getAllByRole("button", { name: "削除" })[0]);

    await waitFor(() => expect(window.confirm).toHaveBeenCalledWith('"Visible" を削除しますか?'));
    expect(taskListTitles()).toEqual(["Visible", "Hidden"]);
    expect(storedTasks()).toHaveLength(2);
    expect(screen.queryByRole("status")).toBeNull();
    expect(window.location.hash).toBe("#/tasks");
  });

  it("bulk deletes selected tasks and shows a notice", async () => {
    seedStoredTasks(
      task({ id: "task-1", title: "Visible", areaId: "do" }),
      task({ id: "task-2", title: "Hidden", areaId: "done", status: "done" }),
      task({ id: "task-3", title: "Later", areaId: "schedule" })
    );
    window.location.hash = "#/tasks";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();

    fireEvent.click(screen.getByRole("checkbox", { name: "Visible を選択" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Later を選択" }));
    fireEvent.click(screen.getByRole("button", { name: "選択したタスクを削除" }));

    await waitFor(() =>
      expect(screen.getByRole("status").textContent).toContain("選択したタスクを削除しました")
    );
    expect(window.confirm).toHaveBeenCalledWith("2件のタスクを削除しますか?");
    expect(taskListTitles()).toEqual(["Hidden"]);
    expect(screen.getByLabelText("現在の選択件数").textContent).toBe("0件選択中");
    expect(screen.getByRole("button", { name: "選択したタスクを削除" })).toHaveProperty(
      "disabled",
      true
    );
    expect(screen.queryByText("選択中")).toBeNull();
  });

  it("shows not-found for a deleted task detail route after bulk delete", async () => {
    seedStoredTasks(
      task({ id: "task-1", title: "Visible", areaId: "do" }),
      task({ id: "task-2", title: "Hidden", areaId: "done", status: "done" })
    );
    window.location.hash = "#/tasks";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();

    fireEvent.click(screen.getByRole("checkbox", { name: "Visible を選択" }));
    fireEvent.click(screen.getByRole("button", { name: "選択したタスクを削除" }));

    await waitFor(() =>
      expect(screen.getByRole("status").textContent).toContain("選択したタスクを削除しました")
    );

    window.location.hash = "#/tasks/task-1";
    fireEvent(window, new HashChangeEvent("hashchange"));

    expect(
      await screen.findByRole("heading", { name: "タスクが見つかりませんでした" })
    ).toBeTruthy();
    expect(screen.getByText("指定された taskId は存在しないか、すでに削除されています。")).toBeTruthy();
  });

  it("keeps selection and tasks when bulk delete confirmation is canceled", async () => {
    seedStoredTasks(
      task({ id: "task-1", title: "Visible", areaId: "do" }),
      task({ id: "task-2", title: "Hidden", areaId: "done", status: "done" })
    );
    window.location.hash = "#/tasks";
    vi.mocked(window.confirm).mockReturnValueOnce(false);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();

    fireEvent.click(screen.getByRole("checkbox", { name: "Visible を選択" }));
    fireEvent.click(screen.getByRole("button", { name: "選択したタスクを削除" }));

    await waitFor(() => expect(window.confirm).toHaveBeenCalledWith("1件のタスクを削除しますか?"));
    expect(taskListTitles()).toEqual(["Visible", "Hidden"]);
    expect(screen.getByLabelText("現在の選択件数").textContent).toBe("1件選択中");
    expect(screen.getByRole("button", { name: "選択したタスクを削除" })).toHaveProperty(
      "disabled",
      false
    );
    expect(storedTasks()).toHaveLength(2);
    expect(screen.getByText("選択中")).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("clears the delete notice after leaving the task list", async () => {
    seedStoredTasks(task({ id: "task-1", title: "Visible", areaId: "do" }));
    window.location.hash = "#/tasks";

    render(<App />);

    expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "削除" }));

    await waitFor(() =>
      expect(screen.getByRole("status").textContent).toContain("タスクを削除しました")
    );

    fireEvent.click(screen.getByRole("link", { name: "マトリックス" }));
    expect(await screen.findByLabelText("Task matrix")).toBeTruthy();

    fireEvent.click(screen.getByRole("link", { name: "タスク一覧" }));
    expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
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
        id: "task-1",
        title: "First task",
        areaId: "schedule",
        order: 0,
        listOrder: 0,
        status: "active"
      },
      {
        id: "task-2",
        title: "Second task",
        areaId: "do",
        order: 0,
        listOrder: 1,
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
    "transitions tasks to %s after a matrix drop and removes them from the matrix view",
    async (terminalAreaId) => {
      seedStoredTasks(
        task({ id: "task-1", title: `${terminalAreaId} task`, areaId: "do" })
      );
      render(<App />);

      expect(await screen.findByText(`${terminalAreaId} task`)).toBeTruthy();
      expect(taskTitlesIn("Do tasks")).toEqual([`${terminalAreaId} task`]);

      dragTaskOverArea("task-1", terminalAreaId);

      await waitFor(() =>
        expect(screen.queryByText(`${terminalAreaId} task`)).toBeNull()
      );
      expect(taskTitlesIn("Do tasks")).toEqual([]);
      expect(storedTasks()[0]).toMatchObject({
        areaId: "do",
        status: terminalAreaId
      });

      fireEvent.click(screen.getByRole("link", { name: "タスク一覧" }));

      expect(await screen.findByRole("heading", { name: "タスク一覧" })).toBeTruthy();
      expect(screen.getByRole("button", { name: terminalAreaId })).toBeTruthy();
      expect(taskListTitles()).toEqual([`${terminalAreaId} task`]);
    }
  );

  it("keeps matrix move behavior unchanged after hiding a task in its original area", async () => {
    seedStoredTasks(
      task({ id: "task-1", title: "Hidden later", areaId: "do", order: 0 }),
      task({ id: "task-2", title: "Move me", areaId: "do", order: 1 }),
      task({ id: "task-3", title: "Scheduled task", areaId: "schedule", order: 0 })
    );
    render(<App />);

    expect(await screen.findByText("Hidden later")).toBeTruthy();

    dragTaskOverArea("task-1", "done");
    await waitFor(() => expect(screen.queryByText("Hidden later")).toBeNull());

    dragTaskOverTask("task-2", "task-3");
    await waitFor(() =>
      expect(taskTitlesIn("Schedule tasks")).toEqual(["Move me", "Scheduled task"])
    );

    expect(storedTasks()).toMatchObject([
      { id: "task-1", areaId: "do", order: 1, status: "done" },
      { id: "task-2", areaId: "schedule", order: 0, status: "active" },
      { id: "task-3", areaId: "schedule", order: 1, status: "active" }
    ]);
    expect(taskTitlesIn("Do tasks")).toEqual([]);
  });

  it("keeps matrix reorder behavior unchanged after hiding a sibling task", async () => {
    seedStoredTasks(
      task({ id: "task-1", title: "Hide me", areaId: "do", order: 0 }),
      task({ id: "task-2", title: "Second task", areaId: "do", order: 1 }),
      task({ id: "task-3", title: "Third task", areaId: "do", order: 2 })
    );
    render(<App />);

    expect(await screen.findByText("Hide me")).toBeTruthy();

    dragTaskOverArea("task-1", "skipped");
    await waitFor(() => expect(screen.queryByText("Hide me")).toBeNull());

    dragTaskOverTask("task-3", "task-2");
    await waitFor(() =>
      expect(taskTitlesIn("Do tasks")).toEqual(["Third task", "Second task"])
    );

    expect(storedTasks()).toMatchObject([
      { id: "task-1", areaId: "do", order: 2, status: "skipped" },
      { id: "task-2", areaId: "do", order: 1, status: "active" },
      { id: "task-3", areaId: "do", order: 0, status: "active" }
    ]);
  });

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

function taskListTitles(): string[] {
  return Array.from(screen.getAllByRole("heading", { level: 3 })).map(
    (item) => item.textContent ?? ""
  );
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
