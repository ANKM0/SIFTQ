import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";

async function signIn(page: Page) {
  await page.goto("/ideas");
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

async function openIdeaModal(page: Page, title: string) {
  await page.locator(".idea-card").filter({ hasText: title }).locator("h2").click();
  await expect(page.locator("[data-idea-modal]")).toBeVisible();
}

async function clickBackdrop(page: Page) {
  const box = await page.locator("[data-idea-modal]").boundingBox();
  if (!box) throw new Error("idea detail modal has no bounding box");
  await page.mouse.click(box.x - 10, box.y + box.height / 2);
}

test("closes the idea detail modal when clicking the backdrop and saves the draft", async ({ page }) => {
  await signIn(page);
  await clearIdeas(page);
  await createIdea(page, "外側クリック");
  await page.goto("/ideas");

  await openIdeaModal(page, "外側クリック");
  await page.locator("[data-idea-modal] input[name='title']").fill("外側クリック更新");

  const saved = page.waitForResponse(
    (response) =>
      response.url().includes("/api/ideas/") &&
      response.request().method() === "PATCH" &&
      (response.request().postData() ?? "").includes("外側クリック更新"),
  );
  await clickBackdrop(page);
  await saved;
  await expect(page.locator("[data-idea-modal]")).toBeHidden();

  await expect(page.locator(".idea-card").filter({ hasText: "外側クリック更新" })).toHaveCount(1);
});

test("keeps the idea detail modal open when clicking inside it", async ({ page }) => {
  await signIn(page);
  await clearIdeas(page);
  await createIdea(page, "内側クリック");
  await page.goto("/ideas");

  await openIdeaModal(page, "内側クリック");
  const modal = page.locator("[data-idea-modal]");
  await modal.locator("input[name='title']").click();
  await expect(modal).toBeVisible();
  await modal.locator("[data-description-editor]").click();
  await expect(modal).toBeVisible();
});

test("keeps the Escape and close button behaviour of the idea detail modal", async ({ page }) => {
  await signIn(page);
  await clearIdeas(page);
  await createIdea(page, "既存操作");
  await page.goto("/ideas");

  await openIdeaModal(page, "既存操作");
  await page.keyboard.press("Escape");
  await expect(page.locator("[data-idea-modal]")).toBeHidden();

  await openIdeaModal(page, "既存操作");
  const saved = page.waitForResponse(
    (response) => response.url().includes("/api/ideas/") && response.request().method() === "PATCH",
  );
  await page.locator("[data-idea-modal] [data-idea-close]").click();
  await saved;
  await expect(page.locator("[data-idea-modal]")).toBeHidden();
});
