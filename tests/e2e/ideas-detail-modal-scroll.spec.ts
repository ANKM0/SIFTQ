import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";

const password = atob("dGVzdC1wYXNzd29yZA==");

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/ideas$/);
}

async function clearIdeas(page: Page) {
  const ideas = await page.evaluate(async () => {
    const response = await fetch("/api/ideas");
    return response.json();
  });
  for (const idea of ideas) {
    await page.evaluate(async (id) => {
      await fetch(`/api/ideas/${id}`, { method: "DELETE" });
    }, idea.id);
  }
}

async function createIdea(page: Page, title: string, description = ""): Promise<{ id: string }> {
  return page.evaluate(async ({ title: ideaTitle, description: ideaDescription }) => {
    const response = await fetch("/api/ideas", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: ideaTitle, description: ideaDescription }),
    });
    if (!response.ok) throw new Error(`create idea failed: ${response.status}`);
    return response.json();
  }, { title, description });
}

function canScroll(page: Page, selector: string | null) {
  return page.evaluate((target) => {
    if (target === null) {
      const overflowY = getComputedStyle(document.documentElement).overflowY;
      if (overflowY === "hidden" || overflowY === "clip") return false;
      const content = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
      return content > window.innerHeight + 1;
    }
    const element = document.querySelector(target);
    if (!element) throw new Error(`missing element: ${target}`);
    const overflowY = getComputedStyle(element).overflowY;
    if (overflowY !== "auto" && overflowY !== "scroll") return false;
    return element.scrollHeight > element.clientHeight + 1;
  }, selector);
}

test("keeps a single scrollbar on the description editor in the idea detail modal", async ({ page }) => {
  await signIn(page);
  await clearIdeas(page);
  const description = Array.from({ length: 80 }, (_value, index) => `行 ${index + 1}`).join("\n");
  await createIdea(page, "スクロール", description);
  await page.goto("/ideas");

  await expect(page.locator(".idea-card").filter({ hasText: "スクロール" })).toHaveCount(1);
  expect(await canScroll(page, null)).toBe(true);

  await page.locator(".idea-card").filter({ hasText: "スクロール" }).locator("h2").click();
  await expect(page.locator("[data-idea-modal]")).toBeVisible();

  expect(await canScroll(page, null)).toBe(false);
  expect(await canScroll(page, "[data-idea-modal]")).toBe(false);
  expect(await canScroll(page, "[data-idea-modal] .idea-detail__form")).toBe(false);
  expect(await canScroll(page, "[data-idea-modal] [data-description-editor]")).toBe(true);

  await page.locator("[data-idea-modal] [data-idea-close]").click();
  await expect(page.locator("[data-idea-modal]")).not.toBeVisible();
  expect(await canScroll(page, null)).toBe(true);
});

test("keeps the standalone idea detail page layout unchanged", async ({ page }) => {
  await signIn(page);
  await clearIdeas(page);
  const description = Array.from({ length: 80 }, (_value, index) => `行 ${index + 1}`).join("\n");
  const idea = await createIdea(page, "単体詳細", description);
  await page.goto(`/ideas/${idea.id}`);

  const form = page.locator(".page--idea-detail .idea-detail__form");
  await expect(form).toBeVisible();
  expect(await form.evaluate((element) => getComputedStyle(element).display)).toBe("block");

  const editor = page.locator(".page--idea-detail [data-description-editor]");
  expect(await editor.evaluate((element) => getComputedStyle(element).maxHeight)).not.toBe("none");
  expect(await canScroll(page, ".page--idea-detail [data-description-editor]")).toBe(true);
});
