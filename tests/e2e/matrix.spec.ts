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

function descriptionEditor(page: Page) {
  return page.getByRole("textbox", { name: "Description" });
}

async function createMatrixTask(page: Page, title: string) {
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
}

async function expectTaskVisibleInList(page: Page, title: string, status: string) {
  await page.goto(`/tasks?status=${status}`);
  for (let attempt = 0; attempt < 20; attempt += 1) {
    if ((await page.getByText(title, { exact: true }).count()) > 0) return;
    const next = page.getByRole("link", { name: "Next page" });
    if ((await next.count()) === 0) break;
    await next.click();
  }
  await expect(page.getByText(title, { exact: true })).toBeVisible();
}

async function openTaskFromList(page: Page, title: string, status: string) {
  await expectTaskVisibleInList(page, title, status);
  await page.getByText(title, { exact: true }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
}

async function expectTaskAbsentFromList(page: Page, title: string, status: string) {
  await page.goto(`/tasks?status=${status}`);
  for (let attempt = 0; attempt < 20; attempt += 1) {
    await expect(page.getByText(title, { exact: true })).toHaveCount(0);
    const next = page.getByRole("link", { name: "Next page" });
    if ((await next.count()) === 0) return;
    await next.click();
  }
  await expect(page.getByText(title, { exact: true })).toHaveCount(0);
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
  await expectTaskVisibleInList(page, title, "done");
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
  await expectTaskVisibleInList(page, title, "skip");
  await expect(page.locator(".task-row").filter({ hasText: title }).locator(".status--skip")).toBeVisible();
});

test("shows the Matrix task action menu in delete, skip, done order", async ({ page }) => {
  const title = `E2E menu order ${Date.now()}`;
  await signIn(page);
  await createMatrixTask(page, title);

  const card = page.locator(".task-card", { hasText: title });
  await card.click({ button: "right" });
  const menu = page.locator(".matrix-menu");
  await expect(menu).toBeVisible();
  await expect(menu.locator("[data-matrix-action]")).toHaveText(["delete", "skip", "done"]);
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

  await expectTaskAbsentFromList(page, title, "do");
});

test("creates a task and sees it in the list", async ({ page }) => {
  const taskTitle = `E2E task ${Date.now()}`;

  await signIn(page);
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(taskTitle);
  await descriptionEditor(page).fill("created by Playwright");
  await page.getByRole("button", { name: "Create" }).click();

  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await expectTaskVisibleInList(page, taskTitle, "do");
});

test("opens description URLs with native link behavior", async ({ page }) => {
  const taskTitle = `E2E description links ${Date.now()}`;
  const taskUrl = "http://127.0.0.1:4173/tasks";

  await signIn(page);
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(taskTitle);
  await descriptionEditor(page).fill(`Open ${taskUrl} or ${taskUrl}`);
  await page.getByRole("button", { name: "Create" }).click();

  await page.locator(".task-card", { hasText: taskTitle }).click();
  const links = descriptionEditor(page).locator("a");
  await expect(links).toHaveCount(2);
  await expect(links.first()).toHaveAttribute("href", taskUrl);

  const popupPromise = page.waitForEvent("popup");
  await links.nth(1).click({ modifiers: ["Control"] });
  const popup = await popupPromise;
  await expect(popup).toHaveURL(/\/tasks$/);
  await popup.close();

  await links.first().click();
  await expect(page).toHaveURL(/\/tasks$/);
});

test("linkifies pasted URLs and submits plain text", async ({ page }) => {
  const taskTitle = `E2E pasted description URL ${Date.now()}`;
  const taskUrl = "http://127.0.0.1:4173/tasks";
  const description = `Pasted ${taskUrl}`;

  await signIn(page);
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(taskTitle);

  const editor = descriptionEditor(page);
  await editor.click();
  await editor.evaluate((element, text) => {
    const range = document.createRange();
    range.selectNodeContents(element);
    range.collapse(false);
    const selection = window.getSelection();
    if (!selection) throw new Error("Selection is unavailable");
    selection.removeAllRanges();
    selection.addRange(range);
    const data = new DataTransfer();
    data.setData("text/plain", text);
    element.dispatchEvent(new ClipboardEvent("paste", { bubbles: true, clipboardData: data }));
  }, description);

  await expect(editor.locator("a")).toHaveAttribute("href", taskUrl);
  await page.getByRole("button", { name: "Create" }).click();
  await page.locator(".task-card", { hasText: taskTitle }).click();

  await expect(descriptionEditor(page).locator("a")).toHaveAttribute("href", taskUrl);
  await expect(page.locator('textarea[data-description-value]')).toHaveValue(description);
});

test("deletes text before a description URL at the URL boundary", async ({ page }) => {
  const taskTitle = `E2E description URL backspace ${Date.now()}`;
  const taskUrl = "https://example.com/tasks";
  const description = `Before ${taskUrl}`;
  const expectedDescription = `Before${taskUrl}`;

  await signIn(page);
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(taskTitle);
  await descriptionEditor(page).fill(description);
  await page.getByRole("button", { name: "Create" }).click();

  await page.locator(".task-card", { hasText: taskTitle }).click();
  const editor = descriptionEditor(page);
  const urlLink = editor.locator("a", { hasText: taskUrl });
  await expect(urlLink).toHaveCount(1);
  await urlLink.evaluate((element) => {
    const editor = element.closest("[data-description-editor]");
    if (!(editor instanceof HTMLElement)) throw new Error("Description editor is unavailable");
    editor.focus();

    const range = document.createRange();
    range.setStartBefore(element);
    range.collapse(true);
    const selection = window.getSelection();
    if (!selection) throw new Error("Selection is unavailable");
    selection.removeAllRanges();
    selection.addRange(range);
  });

  await page.keyboard.press("Backspace");

  await expect(editor).toHaveText(expectedDescription);
  await expect(page.locator('textarea[data-description-value]')).toHaveValue(expectedDescription);
});

test("creates exactly one task with Ctrl+Enter from the title or description", async ({ page }) => {
  await signIn(page);

  for (const field of ["Title", "Description"] as const) {
    const taskTitle = `E2E shortcut ${field} ${Date.now()}`;
    await page.getByRole("link", { name: "New task" }).click();
    await page.getByLabel("Title").fill(taskTitle);
    if (field === "Description") await descriptionEditor(page).fill("created by shortcut");
    await (field === "Description" ? descriptionEditor(page) : page.getByLabel(field)).press("Control+Enter");

    await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
    await expect(page.locator(".task-card", { hasText: taskTitle })).toHaveCount(1);
  }
});

test("saves exactly one task with Ctrl+Enter from the detail form", async ({ page }) => {
  const originalTitle = `E2E detail shortcut ${Date.now()}`;
  const updatedTitle = `${originalTitle} updated`;

  await signIn(page);
  await createMatrixTask(page, originalTitle);
  await page.locator(".task-card", { hasText: originalTitle }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();

  await page.getByLabel("Title").fill(updatedTitle);
  await descriptionEditor(page).press("Control+Enter");

  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await expect(page.locator(".task-card", { hasText: updatedTitle })).toHaveCount(1);
});

test("keeps native task validation on Ctrl+Enter", async ({ page }) => {
  await signIn(page);
  await page.getByRole("link", { name: "New task" }).click();
  await descriptionEditor(page).fill("description without a title");
  await descriptionEditor(page).press("Control+Enter");

  await expect(page.getByRole("heading", { name: "New task" })).toBeVisible();
  const titleIsInvalid = await page.getByLabel("Title").evaluate(
    (element) => element instanceof HTMLInputElement && !element.validity.valid,
  );
  expect(titleIsInvalid).toBe(true);
});

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

  await page.goto("/");
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

  await page.goto("/tasks/new");
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: "Create" }).click();
  await openTaskFromList(page, title, "do");

  const version = page.locator("#task-version");
  const beforeMetaChange = await version.inputValue();
  await page.getByRole("link", { name: new RegExp(`^${kind === "status" ? "Status" : "Area"}`) }).click();
  await page.locator(`[aria-label="Apply ${kind} to this task"] .status-choice`, { hasText: value }).click();
  await expect(version).not.toHaveValue(beforeMetaChange);
  await page.getByLabel("Title").fill(`${title} saved`);
  await page.getByRole("button", { name: "Save" }).click();

  await expect(page).toHaveURL(/\/tasks$/);
  if (kind === "status") {
    await expectTaskVisibleInList(page, `${title} saved`, value);
  } else {
    await expectTaskVisibleInList(page, `${title} saved`, "do");
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
