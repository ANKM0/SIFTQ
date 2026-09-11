import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

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

test.describe("task list bulk actions", () => {
  test("changes the status of selected tasks", async ({ page }) => {
    const suffix = Date.now();
    const titles = [`bulk status one ${suffix}`, `bulk status two ${suffix}`];
    const firstTitle = titles[0];
    if (!firstTitle) throw new Error("The bulk status scenario must include a task.");
    await signIn(page);
    for (const title of titles) await createTask(page, title);

    await page.goto("/tasks?q=is:do");
    for (const title of titles) {
      await page.locator("[data-task-row]", { hasText: title }).getByRole("checkbox").check();
    }
    await page.getByText("Mark as", { exact: true }).click();
    await page.locator('[data-task-action="done"]').click();

    await expect(page.locator("[data-task-row]", { hasText: firstTitle })).toHaveCount(0);
    await page.goto("/tasks?q=is:done");
    for (const title of titles) await expect(page.getByText(title, { exact: true })).toBeVisible();
  });

  test("confirms and cancels bulk deletion", async ({ page }) => {
    const title = `bulk delete ${Date.now()}`;
    await signIn(page);
    await createTask(page, title);
    await page.goto("/tasks?q=is:do");

    const row = page.locator("[data-task-row]", { hasText: title });
    await row.getByRole("checkbox").check();
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
