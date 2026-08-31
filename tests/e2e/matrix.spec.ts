import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const password = atob("dGVzdC1wYXNzd29yZA==");

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
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

test("creates a task and sees it in the list", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill("E2E task");
  await page.getByLabel("Description").fill("created by Playwright");
  await page.getByRole("button", { name: "Create" }).click();

  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await expect(page.getByLabel("Title")).toHaveValue("E2E task");

  await page.goto("/tasks");
  await expect(page.getByText("E2E task")).toBeVisible();
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

  await page.goto("/tasks/new?status=do&area=2");
  await page.getByLabel("Title").fill("E2E popover task");
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();

  await dismissPopover(page, "status");
  await expect(page.locator("#task-meta .status--do")).toHaveText("do");

  await dismissPopover(page, "area");
  await expect(page.locator("#task-meta .area-badge")).toHaveText("2");
});

test("persists an edit and displays a conflict from a stale editor", async ({ page }) => {
  await signIn(page);

  await page.goto("/tasks/new?status=do&area=2");
  await page.getByLabel("Title").fill("E2E concurrent task");
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();

  const staleEditor = await page.context().newPage();
  await staleEditor.goto(page.url());
  await expect(staleEditor.getByLabel("Title")).toHaveValue("E2E concurrent task");

  await page.getByLabel("Title").fill("E2E saved task");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByLabel("Title")).toHaveValue("E2E saved task");

  await staleEditor.getByLabel("Title").fill("E2E stale task");
  await staleEditor.getByRole("button", { name: "Save" }).click();
  await expect(staleEditor.getByText("Task was updated elsewhere.")).toBeVisible();
  await expect(staleEditor.getByRole("link", { name: "Load latest" })).toBeVisible();
});
