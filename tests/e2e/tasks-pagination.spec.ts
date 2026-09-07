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

async function seedDoTasks(page: Page, runId: string, count: number) {
  const statuses = await page.evaluate<number[], [string, number]>(
    async ([seedRunId, seedCount]) => {
      const created: number[] = [];
      for (let index = 1; index <= seedCount; index += 1) {
        const response = await fetch("/api/tasks", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ title: `E2E paging ${seedRunId} ${index}`, description: "" }),
        });
        created.push(response.status);
      }
      return created;
    },
    [runId, count],
  );
  expect(statuses.every((status) => status === 201)).toBe(true);
}

test("shows 25 tasks per page with page navigation", async ({ page }) => {
  await signIn(page);
  await seedDoTasks(page, `nav-${Date.now()}`, 26);

  await page.goto("/tasks?status=do");
  await expect(page.locator(".task-row")).toHaveCount(25);

  const nav = page.getByRole("navigation", { name: "Task list pages" });
  await expect(nav).toBeVisible();
  await expect(nav.locator('[aria-current="page"]')).toHaveText("1");
  await expect(nav.getByRole("link", { name: "Page 2" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Next page" })).toBeVisible();
});

test("moves between pages with page numbers and previous/next links", async ({ page }) => {
  await signIn(page);
  await seedDoTasks(page, `move-${Date.now()}`, 26);

  await page.goto("/tasks?status=do");
  const firstPageTitles = await page.locator(".task-row").allTextContents();

  await page.getByRole("link", { name: "Page 2" }).click();
  await expect(page).toHaveURL(/\/tasks\?status=do&page=2/);
  const secondPageRows = page.locator(".task-row");
  expect(await secondPageRows.count()).toBeGreaterThanOrEqual(1);
  expect(await secondPageRows.count()).toBeLessThanOrEqual(25);
  const secondPageTitles = await secondPageRows.allTextContents();
  expect(secondPageTitles).not.toEqual(firstPageTitles);

  await page.getByRole("link", { name: "Previous page" }).click();
  await expect(page).toHaveURL(/\/tasks\?status=do&page=1/);
  await expect(page.locator(".task-row")).toHaveCount(25);
});

test("falls back to page 1 for a non-numeric page", async ({ page }) => {
  await signIn(page);

  await page.goto("/tasks?status=do&page=abc");
  await expect(page.locator(".task-row").first()).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Task list pages" }).locator('[aria-current="page"]')).toHaveText(
    "1",
  );
});

test("returns to page 1 when switching status", async ({ page }) => {
  await signIn(page);

  await page.goto("/tasks?status=do&page=2");
  await page.locator('a[href="/tasks?status=done"]').click();
  await expect(page).toHaveURL("/tasks?status=done");
});
