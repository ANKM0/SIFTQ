import type { Page } from "@playwright/test";
import { signIn, descriptionEditor, hasDraft, getTaskDraftKey, expectDraftSaved, expectDraftNotSaved, waitForPageSettle, expectTaskVisibleInList, openTaskFromList, dismissPopover } from "./matrix-helpers";
import { expect, test } from "./fixtures";

test("creates a task from the task list and returns to the task list", async ({ page }) => {
  const taskTitle = `E2E list task ${Date.now()}`;

  await signIn(page);
  await page.goto("/tasks");
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(taskTitle);
  await page.getByRole("button", { name: "Create" }).click();

  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
  await expectTaskVisibleInList(page, taskTitle, "do");
});
test("filters the task list by status and retains it after reload", async ({ page }) => {
  await signIn(page);

  const suffix = Date.now();
  for (const status of ["do", "done", "skip"] as const) {
    const title = `E2E filter ${status} ${suffix}`;
    await page.goto(`/tasks/new?status=${status}`);
    await page.getByLabel("Title").fill(title);
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
  }

  await page.goto("/tasks");
  await expect(page.getByText(`E2E filter done ${suffix}`, { exact: true })).not.toBeVisible();
  await expect(page.getByText(`E2E filter skip ${suffix}`, { exact: true })).not.toBeVisible();
  await expectTaskVisibleInList(page, `E2E filter do ${suffix}`, "do");

  await page.locator('a[href="/tasks?status=done"]').click();
  await expect(page).toHaveURL(/\/tasks\?status=done$/);
  await expectTaskVisibleInList(page, `E2E filter done ${suffix}`, "done");

  await page.reload();
  await expect(page).toHaveURL(/\/tasks\?status=done$/);
  await expectTaskVisibleInList(page, `E2E filter done ${suffix}`, "done");

  await page.goto("/matrix");
  await page.locator('nav.nav a[href="/tasks"]').click();
  await expect(page).toHaveURL(/\/tasks$/);
  await expect(page.locator('a[href="/tasks?status=do"][aria-current="true"]')).toBeVisible();
  await expectTaskVisibleInList(page, `E2E filter do ${suffix}`, "do");
});
test("keeps new-task inputs while changing Status and Area", async ({ page }) => {
  const title = `Retained title ${Date.now()}`;
  await signIn(page);

  await page.goto("/tasks/new");
  await page.getByLabel("Title").fill(title);
  await descriptionEditor(page).fill("Retained description");

  await page.locator("#new-task-meta details").first().locator("summary").click();
  await page.locator('input[name="status"][value="done"]').check();
  await expect(page.getByLabel("Title")).toHaveValue(title);
  await expect(descriptionEditor(page)).toHaveText("Retained description");

  await page.locator("#new-task-meta details").nth(1).locator("summary").click();
  await page.locator('input[name="area"][value="4"]').check();
  await expect(page.getByLabel("Title")).toHaveValue(title);
  await expect(descriptionEditor(page)).toHaveText("Retained description");

  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
  await expectTaskVisibleInList(page, title, "done");
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
  await openTaskFromList(page, title, "do");

  await dismissPopover(page, "status");
  await expect(page.locator("#task-meta .status--do")).toHaveText("do");

  await dismissPopover(page, "area");
  await expect(page.locator("#task-meta .area-badge")).toHaveText("2");
});

async function saveAfterMetaChange(page: Page, kind: "status" | "area", value: string) {
  const title = `E2E ${kind} save ${Date.now()}`;
  const description = `E2E ${kind} draft`;

  await page.goto("/tasks/new");
  await page.getByLabel("Title").fill(title);
  await descriptionEditor(page).fill(description);
  await page.getByRole("button", { name: "Create" }).click();
  await openTaskFromList(page, title, "do");

  const draftTitle = `${title} saved`;
  const draftKey = await getTaskDraftKey(page);
  await page.evaluate(() => localStorage.clear());
  await page.clock.install();
  await page.getByLabel("Title").fill(draftTitle);
  await descriptionEditor(page).fill(description);
  await expectDraftSaved(page, draftTitle, description);

  const version = page.locator("#task-version");
  const beforeMetaChange = await version.inputValue();
  await page.getByRole("link", { name: new RegExp(`^${kind === "status" ? "Status" : "Area"}`) }).click();
  await page.locator(`[aria-label="Apply ${kind} to this task"] .status-choice`, { hasText: value }).click();
  await expect(version).not.toHaveValue(beforeMetaChange);
  await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), draftKey)).toContain(draftTitle);
  await page.getByRole("button", { name: "Save" }).click();

  await expect(page).toHaveURL(/\/tasks$/);
  await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), draftKey)).toBeNull();
  if (kind === "status") {
    await expectTaskVisibleInList(page, draftTitle, value);
  } else {
    await expectTaskVisibleInList(page, draftTitle, "do");
  }
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
  await openTaskFromList(page, title, "do");

  const staleEditor = await page.context().newPage();
  await staleEditor.goto(page.url());
  await expect(staleEditor.getByLabel("Title")).toHaveValue(title);

  await page.getByLabel("Title").fill("E2E saved task");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page).toHaveURL(/\/tasks$/);
  await expectTaskVisibleInList(page, "E2E saved task", "do");

  const staleTitle = "E2E stale task";
  const staleDescription = "draft retained after conflict";
  await staleEditor.clock.install();
  await staleEditor.getByLabel("Title").fill(staleTitle);
  await descriptionEditor(staleEditor).fill(staleDescription);
  await expectDraftSaved(staleEditor, staleTitle, staleDescription);
  await staleEditor.getByRole("button", { name: "Save" }).click();
  await expect(staleEditor.getByText("Task was updated elsewhere.")).toBeVisible();
  await expect(staleEditor.getByRole("link", { name: "Load latest" })).toBeVisible();
  await expect.poll(() => hasDraft(staleEditor, staleTitle, staleDescription)).toBe(true);
});
test("does not keep a new task draft when cancelling from the matrix", async ({ page }) => {
  const title = `E2E cancel draft ${Date.now()}`;
  const description = "draft retained after cancel";

  await signIn(page);
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.getByRole("link", { name: "New task" }).click();
  await expect(page.getByRole("heading", { name: "New task" })).toBeVisible();
  await page.getByLabel("Title").waitFor();
  await waitForPageSettle(page);
  await page.clock.install();
  await page.getByLabel("Title").fill(title);
  await descriptionEditor(page).fill(description);
  await expectDraftNotSaved(page, title, description);

  await page.getByRole("link", { name: "Cancel", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await expect.poll(() => hasDraft(page, title, description)).toBe(false);

  await page.getByRole("link", { name: "New task" }).click();
  await expect(page.getByLabel("Title")).toHaveValue("");
  await expect(descriptionEditor(page)).toHaveText("");
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
test("does not keep a new task draft when navigating to another screen", async ({ page }) => {
  const title = `E2E navigation draft ${Date.now()}`;
  const description = "draft retained after navigation";

  await signIn(page);
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").waitFor();
  await waitForPageSettle(page);
  await page.clock.install();
  await page.getByLabel("Title").fill(title);
  await descriptionEditor(page).fill(description);
  await expectDraftNotSaved(page, title, description);

  await page.locator('nav.nav a[href="/matrix"]').click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await expect.poll(() => hasDraft(page, title, description)).toBe(false);

  await page.getByRole("link", { name: "New task" }).click();
  await expect(page.getByLabel("Title")).toHaveValue("");
  await expect(descriptionEditor(page)).toHaveText("");
});
