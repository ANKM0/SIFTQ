import { expect, test } from "./fixtures";

const password = atob("dGVzdC1wYXNzd29yZA==");

async function signIn(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("creates an idea when the composer modal closes", async ({ page }) => {
  await signIn(page);
  await page.goto("/ideas");
  await page.evaluate(() => localStorage.clear());
  await page.reload();

  const initialCount = await page.locator(".idea-card").count();
  await page.locator(".ideas-composer__trigger").click();
  await page.locator('.ideas-composer input[name="title"]').fill("新しいアイデア");
  await page.locator('.ideas-composer textarea[name="description"]').fill("試しに作成したカード");
  await page.locator(".ideas-composer").getByRole("button", { name: "キャンセル" }).click();

  const created = page.locator(".idea-card").filter({ hasText: "新しいアイデア" });
  await expect(created).toHaveCount(1);
  await expect(created.locator(".idea-card__description")).toHaveText("試しに作成したカード");
  expect(await page.locator(".idea-card").count()).toBe(initialCount + 1);

  await page.locator(".ideas-composer__trigger").click();
  await page.locator('.ideas-composer textarea[name="description"]').fill("タイトルなし");
  await page.mouse.click(5, 5);
  await expect(page.locator(".idea-card").filter({ hasText: "無題" })).toHaveCount(1);
});

test("deletes an idea through the action menu and confirmation", async ({ page }) => {
  await signIn(page);
  await page.goto("/ideas");
  await page.evaluate(() => localStorage.clear());
  await page.reload();

  const initialCount = await page.locator(".idea-card").count();
  const card = page.locator(".idea-card").first();
  await card.locator(".idea-card__more").click();
  await expect(page.locator(".matrix-menu")).toBeVisible();
  await page.locator('.matrix-menu [data-idea-action="delete"]').click();
  await expect(page.locator(".matrix-modal")).toContainText("このメモを削除しますか？");
  await page.locator('[data-idea-modal-action="cancel"]').click();
  await expect(card).toHaveCount(1);

  await card.locator(".idea-card__more").click();
  await page.locator('.matrix-menu [data-idea-action="delete"]').click();
  await page.locator('[data-idea-modal-action="confirm"]').click();
  await expect(card).toHaveCount(0);
  expect(await page.locator(".idea-card").count()).toBe(initialCount - 1);

  await page.reload();
  expect(await page.locator(".idea-card").count()).toBe(initialCount - 1);
});
