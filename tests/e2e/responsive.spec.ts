import { expect, installHtmxRoute, test } from "./fixtures";

const password = atob("dGVzdC1wYXNzd29yZA==");

async function signIn(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

async function expectNoHorizontalOverflow(page: import("@playwright/test").Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

test("keeps Matrix and task forms usable at the responsive widths", async ({ page }) => {
  await installHtmxRoute(page);
  await signIn(page);

  for (const width of [320, 360, 390, 412]) {
    await page.setViewportSize({ width, height: 960 });
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await expect.poll(() => page.locator(".matrix").evaluate((element) =>
      getComputedStyle(element).gridTemplateColumns.trim().split(/\s+/).length,
    )).toBe(1);

    await page.goto("/tasks/new");
    await expect(page.getByRole("heading", { name: "New task" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    expect(await page.locator(".detail-grid").evaluate((element) =>
      getComputedStyle(element).gridTemplateColumns.trim().split(/\s+/).length,
    )).toBe(1);
    await page.locator('details[data-popover-close="status"] > summary').click();
    const popover = page.locator('[aria-label="Apply status to this task"]');
    await expect(popover).toBeVisible();
    const box = await popover.boundingBox();
    if (box === null) throw new Error("Status popover bounds are missing");
    expect(box.x + box.width).toBeLessThanOrEqual(width);
  }

  for (const width of [640, 768, 1024, 1280]) {
    await page.setViewportSize({ width, height: 960 });
    await page.goto("/tasks/new");
    await expect(page.getByRole("heading", { name: "New task" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    const columns = await page.locator(".detail-grid").evaluate((element) =>
      getComputedStyle(element).gridTemplateColumns.trim().split(/\s+/).length,
    );
    expect(columns).toBe(width >= 768 ? 2 : 1);
  }
});
