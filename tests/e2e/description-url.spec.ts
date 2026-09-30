import { signIn, descriptionEditor, waitForPageSettle, createMatrixTask } from "./matrix-helpers";
import { e2eBaseUrl, expect, test } from "./fixtures";

test("opens description URLs with native link behavior", async ({ page }) => {
  const taskTitle = `E2E description links ${Date.now()}`;
  const taskUrl = `${e2eBaseUrl}/tasks`;

  await signIn(page);
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(taskTitle);
  await descriptionEditor(page).fill(`Open ${taskUrl} or ${taskUrl}`);
  await page.getByRole("button", { name: "Create" }).click();

  await page.locator(".task-card", { hasText: taskTitle }).click();
  await waitForPageSettle(page);
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
  const taskUrl = `${e2eBaseUrl}/tasks`;
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
  await waitForPageSettle(page);

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
  await waitForPageSettle(page);
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
    // click() does not wait for the htmx swap; waitForURL alone can resolve
    // before the form is settled (see waitForPageSettle).
    await page.waitForURL(/\/tasks\/new/);
    await page.getByLabel("Title").waitFor();
    await waitForPageSettle(page);
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
  await waitForPageSettle(page);

  await page.getByLabel("Title").fill(updatedTitle);
  await descriptionEditor(page).press("Control+Enter");

  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await expect(page.locator(".task-card", { hasText: updatedTitle })).toHaveCount(1);
});
test("refreshes task detail after browser back before Ctrl+Enter and Save", async ({ page }) => {
  const originalTitle = `E2E browser back ${Date.now()}`;
  const shortcutTitle = `${originalTitle} shortcut`;
  const resavedTitle = `${shortcutTitle} resaved`;
  const saveTitle = `${resavedTitle} saved`;
  const conflictResponses: string[] = [];

  await signIn(page);
  page.on("response", (response) => {
    if (response.status() === 409) conflictResponses.push(response.url());
  });

  await createMatrixTask(page, originalTitle);
  await page.locator(".task-card", { hasText: originalTitle }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await waitForPageSettle(page);
  const initialVersion = await page.locator("#task-version").inputValue();

  await page.getByLabel("Title").fill(shortcutTitle);
  await page.getByLabel("Title").press("Control+Enter");
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.goBack();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await expect(page.getByLabel("Title")).toHaveValue(shortcutTitle);
  await expect(page.locator("#task-version")).not.toHaveValue(initialVersion);
  const shortcutVersion = await page.locator("#task-version").inputValue();

  await page.getByLabel("Title").fill(resavedTitle);
  await page.getByLabel("Title").press("Control+Enter");
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await expect(page.locator(".task-card", { hasText: resavedTitle })).toHaveCount(1);

  await page.goBack();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await expect(page.getByLabel("Title")).toHaveValue(resavedTitle);
  await expect(page.locator("#task-version")).not.toHaveValue(shortcutVersion);

  await page.getByLabel("Title").fill(saveTitle);
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await expect(page.locator(".task-card", { hasText: saveTitle })).toHaveCount(1);
  expect(conflictResponses).toHaveLength(0);
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
