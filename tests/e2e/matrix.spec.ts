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

async function dismissPopover(page: Page, label: "status" | "area") {
  const title = label === "status" ? "Status" : "Area";
  const applyLabel = `Apply ${label} to this task`;

  await page.getByRole("link", { name: new RegExp(`^${title}`) }).click();
  const popover = page.locator(`[aria-label="${applyLabel}"]`);
  await expect(popover).toBeVisible();

  const closeHref = await page.locator("[data-popover-close-href]").getAttribute("data-popover-close-href");
  if (closeHref === null) throw new Error("Missing popover close URL");
  const closeUrl = new URL(closeHref, page.url());

  await Promise.all([
    page.waitForURL((url) => url.pathname === closeUrl.pathname && url.search === closeUrl.search),
    page.getByLabel("Title").click(),
  ]);
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

test("dismisses new task Status and Area popovers when clicking outside", async ({ page }) => {
  await signIn(page);

  await page.goto("/tasks/new");
  await dismissPopover(page, "status");
  await expect(page.locator("#new-task-meta .status--do")).toHaveText("do");

  await dismissPopover(page, "area");
  await expect(page.locator("#new-task-meta .area-badge")).toHaveText("1");
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
  await expect(page.getByLabel("Title")).toHaveValue("E2E saved task");

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
