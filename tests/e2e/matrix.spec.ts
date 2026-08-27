import { expect, test } from "@playwright/test";

test("creates a task and sees it in the list", async ({ page }) => {
  await page.goto("/");
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
