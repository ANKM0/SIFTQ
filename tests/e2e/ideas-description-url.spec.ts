import type { Page } from "@playwright/test";
import { e2eBaseUrl, expect, test } from "./fixtures";

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
  const idea = await page.evaluate(async ({ title: ideaTitle, description: ideaDescription }) => {
    const response = await fetch("/api/ideas", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: ideaTitle, description: ideaDescription }),
    });
    if (!response.ok) throw new Error(`create idea failed: ${response.status}`);
    return response.json();
  }, { title, description });
  return idea;
}

async function openIdeaModal(page: Page, title: string) {
  const card = page.locator(".idea-card").filter({ hasText: title });
  await card.locator("h2").click();
  await expect(page.locator("[data-idea-modal]")).toBeVisible();
}

test("linkifies description URLs in the idea detail modal", async ({ page }) => {
  const url = `${e2eBaseUrl}/ideas`;
  await signIn(page);
  await clearIdeas(page);
  await createIdea(page, "URLメモ", `詳細 ${url}`);
  await page.goto("/ideas");

  await openIdeaModal(page, "URLメモ");
  const editor = page.locator("[data-idea-modal] [data-description-editor]");
  const link = editor.locator("a");
  await expect(link).toHaveCount(1);
  await expect(link).toHaveAttribute("href", url);
  await expect(page.locator("[data-idea-modal] textarea[data-description-value]")).toHaveValue(`詳細 ${url}`);
});

test("opens a description URL in the same tab and a new tab with Ctrl", async ({ page }) => {
  const url = `${e2eBaseUrl}/ideas`;
  await signIn(page);
  await clearIdeas(page);
  await createIdea(page, "URL遷移", `see ${url}`);
  await page.goto("/ideas");

  await openIdeaModal(page, "URL遷移");
  const link = page.locator("[data-idea-modal] [data-description-editor] a");

  const popupPromise = page.waitForEvent("popup");
  await link.click({ modifiers: ["Control"] });
  const popup = await popupPromise;
  await expect(popup).toHaveURL(/\/ideas$/);
  await popup.close();

  await link.click();
  await expect(page).toHaveURL(/\/ideas$/);
});

test("linkifies pasted URLs and saves plain text in the modal", async ({ page }) => {
  const url = `${e2eBaseUrl}/ideas`;
  const description = `Pasted ${url}`;
  await signIn(page);
  await clearIdeas(page);
  await createIdea(page, "貼り付けURL");
  await page.goto("/ideas");

  await openIdeaModal(page, "貼り付けURL");
  const editor = page.locator("[data-idea-modal] [data-description-editor]");
  await editor.click();
  await editor.evaluate((element, text) => {
    const range = document.createRange();
    range.selectNodeContents(element);
    const selection = window.getSelection();
    if (!selection) throw new Error("Selection is unavailable");
    selection.removeAllRanges();
    selection.addRange(range);
    const data = new DataTransfer();
    data.setData("text/plain", text);
    element.dispatchEvent(new ClipboardEvent("paste", { bubbles: true, clipboardData: data }));
  }, description);

  await expect(editor.locator("a")).toHaveAttribute("href", url);
  await expect(page.locator("[data-idea-modal] textarea[data-description-value]")).toHaveValue(description);

  const saved = page.waitForResponse(
    (response) => response.url().includes("/api/ideas/") && response.request().method() === "PATCH",
  );
  await page.locator("[data-idea-modal] [data-idea-close]").click();
  await saved;
  await expect(page.locator("[data-idea-modal]")).toBeHidden();

  await page.reload();
  await openIdeaModal(page, "貼り付けURL");
  await expect(page.locator("[data-idea-modal] [data-description-editor] a")).toHaveAttribute("href", url);
  await expect(page.locator("[data-idea-modal] textarea[data-description-value]")).toHaveValue(description);
});

test("shows the description divider in the modal only when the description is not empty", async ({ page }) => {
  await signIn(page);
  await clearIdeas(page);
  await createIdea(page, "区切り線あり", "本文あり");
  await createIdea(page, "区切り線なし");
  await page.goto("/ideas");

  await openIdeaModal(page, "区切り線あり");
  const filled = page.locator("[data-idea-modal] [data-description-editor]");
  await expect(filled).not.toHaveClass(/idea-detail__description--empty/);
  await expect(filled).toHaveCSS("border-top-width", "1px");

  await page.locator("[data-idea-modal] [data-idea-close]").click();
  await expect(page.locator("[data-idea-modal]")).toBeHidden();

  await openIdeaModal(page, "区切り線なし");
  const empty = page.locator("[data-idea-modal] [data-description-editor]");
  await expect(empty).toHaveClass(/idea-detail__description--empty/);
  await expect(empty).toHaveCSS("border-top-width", "0px");
  await expect(empty).not.toContainText("No description yet.");

  await empty.click();
  await page.keyboard.type("追記");
  await expect(empty).not.toHaveClass(/idea-detail__description--empty/);
  await expect(empty).toHaveCSS("border-top-width", "1px");
});

test("linkifies description URLs on the idea detail page", async ({ page }) => {
  const url = `${e2eBaseUrl}/ideas`;
  await signIn(page);
  await clearIdeas(page);
  const idea = await createIdea(page, "詳細ページURL", `ページ ${url}`);
  await page.goto(`/ideas/${idea.id}`);

  const editor = page.locator("[data-description-editor]");
  const link = editor.locator("a");
  await expect(link).toHaveCount(1);
  await expect(link).toHaveAttribute("href", url);
  await expect(page.locator('textarea[data-description-value]')).toHaveValue(`ページ ${url}`);

  await link.click();
  await expect(page).toHaveURL(/\/ideas$/);
});
