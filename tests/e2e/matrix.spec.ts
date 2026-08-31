import { expect, test } from "@playwright/test";

const password = atob("dGVzdC1wYXNzd29yZA==");

test.describe.configure({ mode: "serial" });

test("creates a task and sees it in the list", async ({ page }) => {
  const taskTitle = `E2E task ${Date.now()}`;

  await page.goto("/login");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(taskTitle);
  await page.getByLabel("Description").fill("created by Playwright");
  await page.getByRole("button", { name: "Create" }).click();

  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await expect(page.getByLabel("Title")).toHaveValue(taskTitle);

  await page.goto("/tasks");
  await expect(page.getByText(taskTitle, { exact: true })).toBeVisible();
});

test("persists an edit and displays a conflict from a stale editor", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();

  await page.goto("/tasks/new?status=do&area=2");
  await page.getByLabel("Title").fill("E2E concurrent task");
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();

  const staleEditor = await page.context().newPage();
  await staleEditor.goto(page.url());
  await expect(staleEditor.getByLabel("Title")).toHaveValue("E2E concurrent task");

  await page.getByLabel("Title").fill("E2E saved task");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByLabel("Title")).toHaveValue("E2E saved task");

  await staleEditor.getByLabel("Title").fill("E2E stale task");
  await staleEditor.getByRole("button", { name: "Save" }).click();
  await expect(staleEditor.getByText("Task was updated elsewhere.")).toBeVisible();
  await expect(staleEditor.getByRole("link", { name: "Load latest" })).toBeVisible();
});
