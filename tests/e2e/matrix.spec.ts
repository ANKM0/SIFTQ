import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const password = atob("dGVzdC1wYXNzd29yZA==");

test.describe.configure({ mode: "serial" });

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL((url) => url.pathname === "/");
  await page.waitForLoadState("networkidle");
}

async function createMatrixTask(page: Page, title: string) {
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
}

async function dismissPopover(page: Page, label: "status" | "area") {
  const title = label === "status" ? "Status" : "Area";
  const applyLabel = `Apply ${label} to this task`;

  await page.getByRole("link", { name: new RegExp(`^${title}`) }).click();
  const popover = page.locator(`[aria-label="${applyLabel}"]`);
  await expect(popover).toBeVisible();

  await page.getByLabel("Title").click();
  await expect(popover).toHaveCount(0);
}

test("navigates to a new task from a matrix quadrant blank area", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  for (const area of [1, 2, 3, 4]) {
    const quadrant = page.locator(`.area--quadrant[data-drop-area="${area}"] .matrix-cards`);
    await quadrant.evaluate((element) => {
      element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    await expect(page).toHaveURL(new RegExp(`/tasks/new\\?area=${area}&from=matrix`));
    await expect(page.locator("#new-task-meta .area-badge")).toHaveText(String(area));

    if (area < 4) await page.goto("/");
  }
});

test("keeps the matrix quadrant creation link working", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.getByRole("link", { name: "Create task in area 3" }).click({ position: { x: 5, y: 5 } });

  await expect(page).toHaveURL(/\/tasks\/new\?area=3/);
  await expect(page.locator("#new-task-meta .area-badge")).toHaveText("3");
});

test("keeps matrix task card navigation working", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  const title = `E2E card ${Date.now()}`;
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await page.locator(".task-card", { hasText: title }).click();

  await expect(page).toHaveURL(/\/tasks\/[^/]+\?from=matrix/);
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await expect(page.getByLabel("Title")).toHaveValue(title);
});

test("changes a Matrix task to done from the context menu", async ({ page }) => {
  await signIn(page);

  const title = `E2E context done ${Date.now()}`;
  await createMatrixTask(page, title);
  const card = page.locator(".task-card", { hasText: title });
  await card.click({ button: "right" });
  await page.locator('.matrix-menu [data-matrix-action="done"]').click();

  await expect(card).toHaveCount(0);
  await page.goto("/tasks");
  await expect(page.getByText(title, { exact: true })).toBeVisible();
  await expect(page.locator(".task-row").filter({ hasText: title }).locator(".status--done")).toBeVisible();
});

test("changes a Matrix task to skip from the context menu", async ({ page }) => {
  await signIn(page);

  const title = `E2E context skip ${Date.now()}`;
  await createMatrixTask(page, title);
  const card = page.locator(".task-card", { hasText: title });
  await card.click({ button: "right" });
  await page.locator('.matrix-menu [data-matrix-action="skip"]').click();

  await expect(card).toHaveCount(0);
  await page.goto("/tasks");
  await expect(page.getByText(title, { exact: true })).toBeVisible();
  await expect(page.locator(".task-row").filter({ hasText: title }).locator(".status--skip")).toBeVisible();
});

test("confirms Matrix task deletion in the centered dialog", async ({ page }) => {
  await signIn(page);

  const title = `E2E context delete ${Date.now()}`;
  await createMatrixTask(page, title);
  const card = page.locator(".task-card", { hasText: title });
  await card.click({ button: "right" });
  await page.locator('.matrix-menu [data-matrix-action="delete"]').click();

  const dialog = page.locator(".matrix-modal");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("このタスクを削除しますか？");
  await expect(page.locator(".matrix-modal-backdrop")).toBeVisible();
  await expect(page.locator(".matrix-menu")).toHaveCount(0);

  await dialog.locator('.matrix-modal-button[data-matrix-modal-action="cancel"]').click();
  await expect(dialog).toHaveCount(0);
  await expect(card).toBeVisible();

  await card.click({ button: "right" });
  await page.locator('.matrix-menu [data-matrix-action="delete"]').click();
  await page.locator('.matrix-modal-button[data-matrix-modal-action="confirm"]').click();
  await expect(card).toHaveCount(0);

  await page.goto("/tasks");
  await expect(page.getByText(title, { exact: true })).toHaveCount(0);
});

test("creates a task and sees it in the list", async ({ page }) => {
  const taskTitle = `E2E task ${Date.now()}`;

  await signIn(page);
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(taskTitle);
  await page.getByLabel("Description").fill("created by Playwright");
  await page.getByRole("button", { name: "Create" }).click();

  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.goto("/tasks");
  await expect(page.getByText(taskTitle, { exact: true })).toBeVisible();
});

test("creates a task from the task list and returns to the task list", async ({ page }) => {
  const taskTitle = `E2E list task ${Date.now()}`;

  await signIn(page);
  await page.goto("/tasks");
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(taskTitle);
  await page.getByRole("button", { name: "Create" }).click();

  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
  await expect(page.getByText(taskTitle, { exact: true })).toBeVisible();
});

test("keeps new-task inputs while changing Status and Area", async ({ page }) => {
  const title = `Retained title ${Date.now()}`;
  await signIn(page);

  await page.goto("/tasks/new");
  await page.getByLabel("Title").fill(title);
  await page.getByLabel("Description").fill("Retained description");

  await page.locator("#new-task-meta details").first().locator("summary").click();
  await page.locator('input[name="status"][value="done"]').check();
  await expect(page.getByLabel("Title")).toHaveValue(title);
  await expect(page.getByLabel("Description")).toHaveValue("Retained description");

  await page.locator("#new-task-meta details").nth(1).locator("summary").click();
  await page.locator('input[name="area"][value="4"]').check();
  await expect(page.getByLabel("Title")).toHaveValue(title);
  await expect(page.getByLabel("Description")).toHaveValue("Retained description");

  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
  await page.getByText(title, { exact: true }).click();
  await expect(page.locator("#task-meta .status--done")).toHaveText("done");
  await expect(page.locator("#task-meta .area-badge")).toHaveText("4");
});

test("dismisses new task Status popover when clicking outside", async ({ page }) => {
  await signIn(page);
  await page.goto("/tasks/new");

  const statusDetails = page.locator("#new-task-meta details").first();
  await statusDetails.locator("summary").click();
  const popover = page.locator('[aria-label="Apply status to this task"]');
  await expect(popover).toBeVisible();

  await page.getByLabel("Title").click();
  await expect(statusDetails).not.toHaveAttribute("open");
  await expect(popover).toBeHidden();
});

test("dismisses new task Area popover when clicking outside", async ({ page }) => {
  await signIn(page);
  await page.goto("/tasks/new");

  const areaDetails = page.locator("#new-task-meta details").nth(1);
  await areaDetails.locator("summary").click();
  const popover = page.locator('[aria-label="Apply area to this task"]');
  await expect(popover).toBeVisible();

  await page.getByLabel("Title").click();
  await expect(areaDetails).not.toHaveAttribute("open");
  await expect(popover).toBeHidden();
});

test("closes new task Status and Area popovers with Cancel without changing selection", async ({
  page,
}) => {
  await signIn(page);
  await page.goto("/tasks/new");

  const statusDetails = page.locator("#new-task-meta details").first();
  await statusDetails.locator("summary").click();
  await page
    .locator('[aria-label="Apply status to this task"] [data-popover-cancel]')
    .click();
  await expect(statusDetails).not.toHaveAttribute("open");
  await expect(page.locator('input[name="status"][value="do"]')).toBeChecked();

  const areaDetails = page.locator("#new-task-meta details").nth(1);
  await areaDetails.locator("summary").click();
  await page.locator('[aria-label="Apply area to this task"] [data-popover-cancel]').click();
  await expect(areaDetails).not.toHaveAttribute("open");
  await expect(page.locator('input[name="area"][value="1"]')).toBeChecked();
});

test("closes new task popover when selecting a choice", async ({ page }) => {
  await signIn(page);
  await page.goto("/tasks/new");

  const statusDetails = page.locator("#new-task-meta details").first();
  await statusDetails.locator("summary").click();
  await page.locator('input[name="status"][value="done"]').check();
  await expect(statusDetails).not.toHaveAttribute("open");
});

test("dismisses task detail Status and Area popovers when clicking outside", async ({ page }) => {
  await signIn(page);

  const title = `E2E popover task ${Date.now()}`;
  await page.goto("/tasks/new?status=do&area=2");
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
  await page.getByText(title, { exact: true }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();

  await dismissPopover(page, "status");
  await expect(page.locator("#task-meta .status--do")).toHaveText("do");

  await dismissPopover(page, "area");
  await expect(page.locator("#task-meta .area-badge")).toHaveText("2");
});

async function saveAfterMetaChange(page: Page, kind: "status" | "area", value: string) {
  const title = `E2E ${kind} save ${Date.now()}`;

  await page.goto("/tasks/new");
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: "Create" }).click();
  await page.getByText(title, { exact: true }).click();

  const version = page.locator("#task-version");
  const beforeMetaChange = await version.inputValue();
  await page.getByRole("link", { name: new RegExp(`^${kind === "status" ? "Status" : "Area"}`) }).click();
  await page.locator(`[aria-label="Apply ${kind} to this task"] .status-choice`, { hasText: value }).click();
  await expect(version).not.toHaveValue(beforeMetaChange);
  await page.getByLabel("Title").fill(`${title} saved`);
  await page.getByRole("button", { name: "Save" }).click();

  await expect(page).toHaveURL(/\/tasks$/);
  await expect(page.getByText(`${title} saved`, { exact: true })).toBeVisible();
}

test("saves after changing task status", async ({ page }) => {
  await signIn(page);

  await saveAfterMetaChange(page, "status", "done");
});

test("saves after changing task area", async ({ page }) => {
  await signIn(page);

  await saveAfterMetaChange(page, "area", "4");
});

test("persists an edit and displays a conflict from a stale editor", async ({ page }) => {
  await signIn(page);

  const title = `E2E concurrent task ${Date.now()}`;
  await page.goto("/tasks/new?status=do&area=2");
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
  await page.getByText(title, { exact: true }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();

  const staleEditor = await page.context().newPage();
  await staleEditor.goto(page.url());
  await expect(staleEditor.getByLabel("Title")).toHaveValue(title);

  await page.getByLabel("Title").fill("E2E saved task");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page).toHaveURL(/\/tasks$/);
  await expect(page.locator(".task-row").filter({ hasText: "E2E saved task" }).first()).toBeVisible();

  await staleEditor.getByLabel("Title").fill("E2E stale task");
  await staleEditor.getByRole("button", { name: "Save" }).click();
  await expect(staleEditor.getByText("Task was updated elsewhere.")).toBeVisible();
  await expect(staleEditor.getByRole("link", { name: "Load latest" })).toBeVisible();
});

test("cancels a new task from the matrix and returns to the matrix", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.getByRole("link", { name: "New task" }).click();
  await expect(page.getByRole("heading", { name: "New task" })).toBeVisible();

  await page.getByRole("link", { name: "Cancel", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
});

test("cancels a new task from the task list and returns to the task list", async ({ page }) => {
  await signIn(page);
  await page.goto("/tasks");
  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();

  await page.getByRole("link", { name: "New task" }).click();
  await expect(page.getByRole("heading", { name: "New task" })).toBeVisible();

  await page.getByRole("link", { name: "Cancel", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
});
