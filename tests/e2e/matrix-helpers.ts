import type { Page } from "@playwright/test";
import { expect } from "./fixtures";

export async function signIn(page: Page) {
  await page.goto("/matrix");
  await page.waitForLoadState("domcontentloaded");
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
}

export function descriptionEditor(page: Page) {
  return page.getByRole("textbox", { name: "Description" });
}

export async function hasDraft(page: Page, title: string, description: string): Promise<boolean> {
  return page.evaluate(({ title, description }) => {
    for (let index = 0; index < localStorage.length; index += 1) {
      const value = localStorage.getItem(localStorage.key(index) ?? "");
      if (value !== null && value.includes(title) && value.includes(description)) return true;
    }
    return false;
  }, { title, description });
}

export async function getTaskDraftKey(page: Page): Promise<string> {
  return page.locator('form[data-task-form="edit"]').evaluate((form) => {
    const match = (form.getAttribute("action") ?? "").match(/\/tasks\/([^/?#]+)/);
    const taskId = match?.[1];
    if (!taskId) throw new Error("Task ID is missing from the edit form action");
    return `siftq.task-draft:${decodeURIComponent(taskId)}`;
  });
}

export async function expectDraftSaved(page: Page, title: string, description: string) {
  // The fake clock advances with real time, so keep a margin around the 500ms boundary.
  await page.clock.fastForward(400);
  expect(await hasDraft(page, title, description)).toBe(false);
  await page.clock.fastForward(200);
  expect(await hasDraft(page, title, description)).toBe(true);
}

export async function expectDraftNotSaved(page: Page, title: string, description: string) {
  // New task drafts are disabled; wait past the save debounce and assert nothing is stored.
  await page.clock.fastForward(600);
  expect(await hasDraft(page, title, description)).toBe(false);
}

export async function waitForPageSettle(page: Page) {
  // A full-page navigation runs its deferred scripts before `load`, so wait for
  // it to attach the form/description handlers before the test interacts.
  await page.waitForLoadState("load");
  // htmx swaps #page and settles (attaching submit handlers to the new form)
  // asynchronously; submitting before htmx:afterSettle falls back to a native
  // GET submit that stays on the form.
  await page.evaluate(() =>
    new Promise<void>((resolve) => {
      if (!document.querySelector(".htmx-settling")) {
        resolve();
        return;
      }
      document.addEventListener("htmx:afterSettle", () => resolve(), { once: true });
    }),
  );
}

export async function disableLocalStorage(page: Page) {
  await page.evaluate(() => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      get() {
        throw new Error("localStorage is unavailable");
      },
    });
  });
}

export async function createMatrixTask(page: Page, title: string) {
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
}

export async function gotoListPage(page: Page, status: string) {
  const target = `/tasks?status=${status}`;
  // A save navigation can still be settling when the list assertion starts.
  // Wait before starting the next navigation to avoid Playwright cancelling it.
  await page.waitForLoadState("load");
  try {
    await page.goto(target, { waitUntil: "load" });
  } catch {
    await page.waitForLoadState("load");
    await page.goto(target, { waitUntil: "load" });
  }
}

export async function expectTaskVisibleInList(page: Page, title: string, status: string) {
  await gotoListPage(page, status);
  for (let attempt = 0; attempt < 20; attempt += 1) {
    if ((await page.getByText(title, { exact: true }).count()) > 0) return;
    const next = page.getByRole("link", { name: "Next page" });
    if ((await next.count()) === 0) break;
    await next.click();
  }
  await expect(page.getByText(title, { exact: true })).toBeVisible();
}

export async function openTaskFromList(page: Page, title: string, status: string) {
  await expectTaskVisibleInList(page, title, status);
  await page.getByText(title, { exact: true }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
}

export async function expectTaskAbsentFromList(page: Page, title: string, status: string) {
  await gotoListPage(page, status);
  for (let attempt = 0; attempt < 20; attempt += 1) {
    await expect(page.getByText(title, { exact: true })).toHaveCount(0);
    const next = page.getByRole("link", { name: "Next page" });
    if ((await next.count()) === 0) return;
    await next.click();
  }
  await expect(page.getByText(title, { exact: true })).toHaveCount(0);
}

export async function dismissPopover(page: Page, label: "status" | "area") {
  const title = label === "status" ? "Status" : "Area";
  const applyLabel = `Apply ${label} to this task`;

  await page.getByRole("link", { name: new RegExp(`^${title}`) }).click();
  const popover = page.locator(`[aria-label="${applyLabel}"]`);
  await expect(popover).toBeVisible();

  await page.getByLabel("Title").click();
  await expect(popover).toHaveCount(0);
}
