import { expect, test } from "@playwright/test";

const password = atob("dGVzdC1wYXNzd29yZA==");

test("creates a task and sees it in the list", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
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
