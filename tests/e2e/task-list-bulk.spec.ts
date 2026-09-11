import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";

const password = atob("dGVzdC1wYXNzd29yZA==");

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL((url) => url.pathname === "/");
}

async function createTask(page: Page, title: string) {
  const status = await page.evaluate(async (taskTitle) => {
    const response = await fetch("/api/tasks", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: taskTitle, description: "" }),
    });
    return response.status;
  }, title);
  expect(status).toBe(201);
}

async function selectTask(page: Page, status: string, title: string): Promise<Locator> {
  await page.goto(`/tasks?status=${status}`);
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const row = page.locator("[data-task-row]", { hasText: title });
    if ((await row.count()) > 0) {
      await row.getByRole("checkbox").check();
      return row;
    }
    const next = page.getByRole("link", { name: "Next page" });
    if ((await next.count()) === 0) break;
    await next.click();
  }
  throw new Error(`Task was not found in the ${status} task list: ${title}`);
}

async function expectTaskVisible(page: Page, status: string, title: string) {
  await page.goto(`/tasks?status=${status}`);
  for (let attempt = 0; attempt < 20; attempt += 1) {
    if ((await page.getByText(title, { exact: true }).count()) > 0) return;
    const next = page.getByRole("link", { name: "Next page" });
    if ((await next.count()) === 0) break;
    await next.click();
  }
  await expect(page.getByText(title, { exact: true })).toBeVisible();
}

test.describe("task list bulk actions", () => {
  test("changes the status of selected tasks", async ({ page }) => {
    const title = `bulk status ${Date.now()}`;
    await signIn(page);
    await createTask(page, title);

    await selectTask(page, "do", title);
    await page.getByText("Mark as", { exact: true }).click();
    await page.locator('[data-task-action="done"]').click();

    await expect(page.locator("[data-task-row]", { hasText: title })).toHaveCount(0);
    await expectTaskVisible(page, "done", title);
  });

  test("confirms and cancels bulk deletion", async ({ page }) => {
    const title = `bulk delete ${Date.now()}`;
    await signIn(page);
    await createTask(page, title);
    const row = await selectTask(page, "do", title);
    await page.getByRole("button", { name: "delete" }).click();
    const dialog = page.locator(".matrix-modal");
    await expect(dialog).toContainText("選択した1件のタスクを削除しますか？");
    await dialog.locator('[data-task-list-delete="cancel"]').click();
    await expect(row).toBeVisible();

    await page.getByRole("button", { name: "delete" }).click();
    await page.locator('[data-task-list-delete="confirm"]').click();
    await expect(page.locator("[data-task-row]", { hasText: title })).toHaveCount(0);
  });
});
