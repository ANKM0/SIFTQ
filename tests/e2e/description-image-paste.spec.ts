import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";

const password = atob("dGVzdC1wYXNzd29yZA==");
const PIXEL_PNG =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL((url) => url.pathname === "/ideas");
}

async function createTask(page: Page, title: string): Promise<string> {
  return page.evaluate(async (taskTitle) => {
    const response = await fetch("/api/tasks", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: taskTitle, description: "" }),
    });
    if (!response.ok) throw new Error(`create task failed: ${response.status}`);
    const task = await response.json();
    return task.id;
  }, title);
}

async function deleteTask(page: Page, id: string): Promise<void> {
  await page.evaluate(async (taskId) => {
    await fetch(`/api/tasks/${taskId}`, {
      method: "DELETE",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ version: 1 }),
    });
  }, id);
}

async function createIdea(page: Page, title: string): Promise<string> {
  return page.evaluate(async (ideaTitle) => {
    const response = await fetch("/api/ideas", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: ideaTitle, description: "" }),
    });
    if (!response.ok) throw new Error(`create idea failed: ${response.status}`);
    const idea = await response.json();
    return idea.id;
  }, title);
}

async function deleteIdea(page: Page, id: string): Promise<void> {
  await page.evaluate(async (ideaId) => {
    await fetch(`/api/ideas/${ideaId}`, { method: "DELETE" });
  }, id);
}

function dispatchPaste(element: Element, encoded: string): void {
  const binary = atob(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  const file = new File([bytes], "pixel.png", { type: "image/png" });
  const transfer = new DataTransfer();
  transfer.items.add(file);
  const event = new Event("paste", { bubbles: true, cancelable: true });
  Object.defineProperty(event, "clipboardData", { value: transfer });
  element.dispatchEvent(event);
}

async function pasteImage(page: Page, selector: string, base64: string): Promise<void> {
  await page.locator(selector).evaluate(dispatchPaste, base64);
}

test("pasting an image into the task description editor saves and renders it", async ({ page }) => {
  await signIn(page);
  const taskId = await createTask(page, `E2E image ${Date.now()}`);

  try {
    await page.goto(`/tasks/${taskId}?from=tasks`);
    const editor = page.locator("[data-description-editor]");
    await pasteImage(page, "[data-description-editor]", PIXEL_PNG);

    const image = editor.locator("img.description-image");
    await expect(image).toHaveCount(1);
    await expect(image).toHaveAttribute("src", /^\/api\/images\//);

    const token = await page.locator("textarea[data-description-value]").inputValue();
    expect(token).toMatch(/^\/api\/images\/[0-9A-Za-z_-]+$/);

    await page.getByRole("button", { name: "Save" }).click();
    await page.waitForLoadState("networkidle");
    await page.goto(`/tasks/${taskId}?from=tasks`);

    await expect(page.locator("[data-description-editor] img.description-image")).toHaveCount(1);
    await page.reload();
    await expect(page.locator("[data-description-editor] img.description-image")).toHaveCount(1);
    await expect(page.locator("textarea[data-description-value]")).toHaveValue(token);
  } finally {
    await deleteTask(page, taskId);
  }
});

test("pasting an image into the idea composer creates a card with the image", async ({ page }) => {
  await signIn(page);
  const title = `E2E composer ${Date.now()}`;

  await page.goto("/ideas");
  await page.locator("[data-idea-composer-trigger]").click();
  await page.locator(".ideas-composer__title").fill(title);
  await pasteImage(page, ".ideas-composer__description", PIXEL_PNG);

  const description = page.locator(".ideas-composer__description");
  await expect(description).toHaveValue(/^\/api\/images\/[0-9A-Za-z_-]+$/);
  await page.locator("[data-idea-composer-close]").click();

  const card = page.locator(".idea-card").filter({ hasText: title });
  await expect(card).toBeVisible();
  await expect(card.locator("img.description-image")).toHaveCount(1);

  await deleteIdea(page, (await card.getAttribute("data-idea-id")) ?? "");
});

test("pasting an image into the idea modal saves and reloads it", async ({ page }) => {
  await signIn(page);
  const title = `E2E modal ${Date.now()}`;
  const ideaId = await createIdea(page, title);

  try {
    await page.goto("/ideas");
    await page.locator(".idea-card").filter({ hasText: title }).locator("h2").click();
    await expect(page.locator("[data-idea-modal]")).toBeVisible();

    await pasteImage(page, "[data-idea-modal] [data-description-editor]", PIXEL_PNG);
    const image = page.locator("[data-idea-modal] [data-description-editor] img.description-image");
    await expect(image).toHaveCount(1);

    await page.locator("[data-idea-modal] [data-idea-close]").click();
    await page.reload();

    await page.locator(".idea-card").filter({ hasText: title }).locator("h2").click();
    await expect(page.locator("[data-idea-modal] [data-description-editor] img.description-image")).toHaveCount(1);
  } finally {
    await deleteIdea(page, ideaId);
  }
});
