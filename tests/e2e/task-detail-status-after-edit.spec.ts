import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";

const password = atob("dGVzdC1wYXNzd29yZA==");

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/$/);
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

async function openDetail(page: Page, title: string) {
  await page.goto("/matrix");
  await page.locator(".task-card", { hasText: title }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
}

async function changeStatus(page: Page, status: "done" | "skip") {
  await page.getByRole("link", { name: /^Status/ }).click();
  await expect(page.locator('[aria-label="Apply status to this task"]')).toBeVisible();
  await page
    .locator('[aria-label="Apply status to this task"] .status-choice', { hasText: status })
    .click();
  await expect(page.locator(`#task-meta .status--${status}`)).toHaveText(status);
  await expect(page.getByLabel("Title")).toBeEditable();
}

test("description update then Status operation stays interactive", async ({ page }) => {
  const title = `E2E 477 description ${Date.now()}`;
  await signIn(page);
  await createMatrixTask(page, title);
  await openDetail(page, title);
  await descriptionEditor(page).fill(`updated description ${Date.now()}`);
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await openDetail(page, title);
  await changeStatus(page, "done");
});

test("title update then Status operation stays interactive", async ({ page }) => {
  const title = `E2E 477 title ${Date.now()}`;
  const updatedTitle = `${title} updated`;
  await signIn(page);
  await createMatrixTask(page, title);
  await openDetail(page, title);
  await page.getByLabel("Title").fill(updatedTitle);
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await openDetail(page, updatedTitle);
  await changeStatus(page, "done");
});

test("area update then Status operation stays interactive", async ({ page }) => {
  const title = `E2E 477 area ${Date.now()}`;
  await signIn(page);
  await createMatrixTask(page, title);
  await openDetail(page, title);
  await page.getByRole("link", { name: /^Area/ }).click();
  await page.locator('[aria-label="Apply area to this task"] .status-choice', { hasText: "4" }).click();
  await expect(page.locator("#task-meta .area-badge")).toHaveText("4");
  await changeStatus(page, "skip");
});

test("description selection left idle does not freeze Status", async ({ page }) => {
  const title = `E2E 477 selection ${Date.now()}`;
  const description = `selected description ${Date.now()}`;
  await signIn(page);
  await createMatrixTask(page, title);
  await openDetail(page, title);
  await descriptionEditor(page).fill(description);

  const editor = descriptionEditor(page);
  await editor.evaluate((element) => {
    const range = document.createRange();
    range.selectNodeContents(element);
    const selection = window.getSelection();
    if (!selection) throw new Error("Selection is unavailable");
    selection.removeAllRanges();
    selection.addRange(range);
  });
  await expect.poll(() => page.evaluate(() => window.getSelection()?.rangeCount ?? 0)).toBe(1);
  await changeStatus(page, "done");
  await expect(editor).toHaveText(description);
});
