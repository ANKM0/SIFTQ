import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";

const password = atob("dGVzdC1wYXNzd29yZA==");

const MAX_HEIGHT_PX = 672;

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

async function createIdea(page: Page, title: string, description = "") {
  const status = await page.evaluate(async ({ title: ideaTitle, description: ideaDescription }) => {
    const response = await fetch("/api/ideas", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: ideaTitle, description: ideaDescription }),
    });
    return response.status;
  }, { title, description });
  expect(status).toBe(201);
}

function longDescription(lines = 200) {
  return Array.from({ length: lines }, (_, index) => `line ${index}`).join("\n");
}

test("grows the composer description with input but caps it at 672px and scrolls", async ({ page }) => {
  await signIn(page);
  await clearIdeas(page);
  await page.goto("/ideas");

  await page.locator(".ideas-composer__trigger").click();
  const description = page.locator('.ideas-composer textarea[name="description"]');
  const initialHeight = (await description.boundingBox())?.height ?? 0;

  await description.fill(longDescription());

  const box = await description.boundingBox();
  const metrics = await description.evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
  }));

  expect(box?.height ?? 0).toBeGreaterThan(initialHeight);
  expect(box?.height ?? 0).toBeLessThanOrEqual(MAX_HEIGHT_PX);
  expect(metrics.scrollHeight).toBeGreaterThan(metrics.clientHeight);
});

test("caps each idea card at 672px and hides the overflowing description", async ({ page }) => {
  await signIn(page);
  await clearIdeas(page);
  await createIdea(page, `高さ上限カード ${Date.now()}`, longDescription());
  await page.goto("/ideas");

  const card = page.locator(".idea-card").first();
  await expect(card).toBeVisible();

  const box = await card.boundingBox();
  expect(box?.height ?? 0).toBeLessThanOrEqual(MAX_HEIGHT_PX);
  await expect(card).toHaveCSS("overflow", "hidden");
});

test("keeps empty and short ideas and the composer at their natural height", async ({ page }) => {
  await signIn(page);
  await clearIdeas(page);
  await createIdea(page, `空カード ${Date.now()}`);
  await createIdea(page, `短文カード ${Date.now()}`, "短い説明");
  await page.goto("/ideas");

  const cards = page.locator(".idea-card");
  await expect(cards).toHaveCount(2);
  for (const card of await cards.all()) {
    const box = await card.boundingBox();
    expect(box?.height ?? 0).toBeLessThan(MAX_HEIGHT_PX);
  }

  await page.locator(".ideas-composer__trigger").click();
  const description = page.locator('.ideas-composer textarea[name="description"]');
  await description.fill("短いメモ");
  const box = await description.boundingBox();
  expect(box?.height ?? 0).toBeLessThan(MAX_HEIGHT_PX);
});
