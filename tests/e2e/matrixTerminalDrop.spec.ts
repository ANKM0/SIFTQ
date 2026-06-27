import { expect, test, type Locator, type Page } from "@playwright/test";

const STORAGE_KEY = "siftq.tasks.v1";

type DropPosition = "top" | "center" | "bottom";
type StoredTask = {
  readonly id: string;
  readonly title: string;
  readonly description: string;
  readonly areaId: "do" | "schedule" | "delegate" | "eliminate" | "done" | "skipped";
  readonly status: "active" | "done" | "skipped";
  readonly order: number;
  readonly createdAt: string;
  readonly updatedAt: string;
  readonly listOrder: number;
};

const dropOffsets: Record<DropPosition, number> = {
  top: 0.15,
  center: 0.5,
  bottom: 0.85
};

for (const terminalArea of ["done", "skipped"] as const) {
  for (const dropPosition of ["top", "center", "bottom"] as const) {
    test(`drops into ${terminalArea} from the ${dropPosition} of the terminal side column`, async ({
      page
    }) => {
      const draggedTaskTitle = `${terminalArea}-${dropPosition}-task`;

      await seedMatrixTasks(page, [
        createTask({
          id: "task-1",
          title: draggedTaskTitle
        }),
        createTask({
          id: "task-2",
          title: "keep-visible",
          areaId: "schedule",
          listOrder: 1
        })
      ]);

      await page.goto("/#/");
      await expect(page.locator('[aria-label="Task matrix"]')).toBeVisible();

      const taskCard = page.locator(".task-card", {
        has: page.locator(".task-card__title", { hasText: draggedTaskTitle })
      });
      const terminalShell = page.locator(`.matrix-workspace__status--${terminalArea}`);

      await dragTaskCardToTerminalShell(taskCard, terminalShell, dropPosition, page);

      await expect(terminalShell).toHaveClass(/status-drop-area-shell--drop-target/);
      await page.mouse.up();

      await expect(taskCard).toHaveCount(0);
      await expect(
        page.locator(".task-card", {
          has: page.locator(".task-card__title", { hasText: "keep-visible" })
        })
      ).toHaveCount(1);

      const storedTask = await readStoredTask(page, "task-1");

      expect(storedTask.status).toBe(terminalArea);
      expect(storedTask.areaId).toBe("do");
    });
  }
}

async function seedMatrixTasks(page: Page, tasks: readonly StoredTask[]) {
  await page.addInitScript(
    ({ storageKey, storedTasks }) => {
      window.localStorage.setItem(
        storageKey,
        JSON.stringify({
          version: 1,
          tasks: storedTasks
        })
      );
    },
    {
      storageKey: STORAGE_KEY,
      storedTasks: tasks
    }
  );
}

async function dragTaskCardToTerminalShell(
  taskCard: Locator,
  terminalShell: Locator,
  dropPosition: DropPosition,
  page: Page
) {
  const cardBounds = await taskCard.boundingBox();
  const shellBounds = await terminalShell.boundingBox();

  if (cardBounds === null || shellBounds === null) {
    throw new Error("Expected draggable card and terminal shell to have layout boxes.");
  }

  const startX = cardBounds.x + cardBounds.width / 2;
  const startY = cardBounds.y + cardBounds.height / 2;
  const endX = shellBounds.x + shellBounds.width / 2;
  const endY = shellBounds.y + shellBounds.height * dropOffsets[dropPosition];

  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(startX + 8, startY + 8, { steps: 4 });
  await page.mouse.move(endX, endY, { steps: 20 });
}

async function readStoredTask(page: Page, taskId: string): Promise<StoredTask> {
  const task = await page.evaluate(
    ({ storageKey, targetTaskId }) => {
      const raw = window.localStorage.getItem(storageKey);

      if (raw === null) {
        return null;
      }

      const parsed = JSON.parse(raw) as { tasks?: StoredTask[] };

      return parsed.tasks?.find((candidate) => candidate.id === targetTaskId) ?? null;
    },
    {
      storageKey: STORAGE_KEY,
      targetTaskId: taskId
    }
  );

  if (task === null) {
    throw new Error(`Stored task ${taskId} was not found.`);
  }

  return task;
}

function createTask(overrides: Partial<StoredTask> & Pick<StoredTask, "id" | "title">): StoredTask {
  return {
    id: overrides.id,
    title: overrides.title,
    description: overrides.description ?? "",
    areaId: overrides.areaId ?? "do",
    status: overrides.status ?? "active",
    order: overrides.order ?? 0,
    createdAt: overrides.createdAt ?? "2024-01-02T03:04:05.000Z",
    updatedAt: overrides.updatedAt ?? "2024-01-02T03:04:05.000Z",
    listOrder: overrides.listOrder ?? 0
  };
}
