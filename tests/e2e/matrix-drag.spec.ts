import { signIn, waitForPageSettle, createMatrixTask, expectTaskVisibleInList, expectTaskAbsentFromList } from "./matrix-helpers";
import { expect, test } from "./fixtures";

test("navigates to a new task from a matrix quadrant blank area", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  for (const area of [1, 2, 3, 4]) {
    const quadrant = page.locator(`.area--quadrant[data-drop-area="${area}"] .matrix-cards`);
    await quadrant.evaluate((element) => {
      element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    await expect(page).toHaveURL(new RegExp(`/tasks/new\\?area=${area}&from=matrix`));
    await expect(page.locator("#new-task-meta .area-badge")).toHaveText(String(area));

    if (area < 4) await page.goto("/matrix");
  }
});
test("keeps the page interactive after dragging and dropping a matrix card", async ({ page }) => {
  await signIn(page);

  const suffix = Date.now();
  const firstTitle = `E2E dnd first ${suffix}`;
  const secondTitle = `E2E dnd second ${suffix}`;
  await createMatrixTask(page, firstTitle);
  await createMatrixTask(page, secondTitle);
  await page.goto("/matrix");
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  const firstCard = page.locator(".task-card", { hasText: firstTitle });
  const secondCard = page.locator(".task-card", { hasText: secondTitle });
  await page.evaluate(() => {
    document.body.dataset["dragstarts"] = "0";
    document.addEventListener("dragstart", () => {
      document.body.dataset["dragstarts"] = String(Number(document.body.dataset["dragstarts"] ?? "0") + 1);
    });
  });
  const reorder = page.waitForResponse(
    (response) => response.url().includes("/api/tasks/reorder") && response.request().method() === "POST",
  );
  await secondCard.dragTo(firstCard, { targetPosition: { x: 5, y: 5 } });
  expect((await reorder).status()).toBe(200);

  // The native HTML5 drag session must never start.
  await expect(page.locator("body")).toHaveAttribute("data-dragstarts", "0");
  // The drag session must end without leaving the page inert.
  await expect(secondCard).not.toHaveClass(/dragging/);
  // The first click after the drop must reach the card instead of being swallowed.
  await secondCard.click();
  await expect(page).toHaveURL(/\/tasks\/[^/]+\?from=matrix/);
});
test("moves a matrix card between quadrants with a pointer drag", async ({ page }) => {
  await signIn(page);

  const title = `E2E cross quadrant ${Date.now()}`;
  await createMatrixTask(page, title);
  await page.goto("/matrix");
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  const card = page.locator(".task-card", { hasText: title });
  const target = page.locator('.area--quadrant[data-drop-area="4"] .matrix-cards');
  const reorder = page.waitForResponse(
    (response) => response.url().includes("/api/tasks/reorder") && response.request().method() === "POST",
  );
  await card.dragTo(target);
  expect((await reorder).status()).toBe(200);

  await page.reload();
  await expect(page.locator('.area--quadrant[data-drop-area="4"] .task-card', { hasText: title })).toBeVisible();
});
test("shows a drag ghost and insertion placeholder during a pointer drag", async ({ page }) => {
  await signIn(page);

  const title = `E2E drag feedback ${Date.now()}`;
  await createMatrixTask(page, title);
  await page.goto("/matrix");
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  const card = page.locator(".task-card", { hasText: title });
  const target = page.locator('.area--quadrant[data-drop-area="4"] .matrix-cards');
  const cardBox = await card.boundingBox();
  const targetBox = await target.boundingBox();
  if (!cardBox || !targetBox) throw new Error("Drag boxes are missing");

  await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(cardBox.x + cardBox.width / 2 + 16, cardBox.y + cardBox.height / 2 + 16, {
    steps: 4,
  });

  const ghost = page.locator(".matrix-drag-ghost");
  await expect(ghost).toBeVisible();
  await expect(ghost).toContainText(title);

  await page.mouse.move(targetBox.x + targetBox.width / 2, targetBox.y + 24, { steps: 6 });
  const quadrant = page.locator('.area--quadrant[data-drop-area="4"]');
  await expect(quadrant).toHaveClass(/drop-target/);
  await expect(quadrant.locator(".matrix-drag-placeholder")).toBeVisible();

  const reorder = page.waitForResponse(
    (response) => response.url().includes("/api/tasks/reorder") && response.request().method() === "POST",
  );
  await page.mouse.up();
  expect((await reorder).status()).toBe(200);

  await expect(page.locator(".matrix-drag-ghost")).toHaveCount(0);
  await expect(page.locator(".matrix-drag-placeholder")).toHaveCount(0);
});
test("clears the drag ghost and placeholder when the pointer is cancelled", async ({ page }) => {
  await signIn(page);

  const title = `E2E drag cancel ${Date.now()}`;
  await createMatrixTask(page, title);
  await page.goto("/matrix");
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.evaluate(() => {
    document.addEventListener("pointerdown", (event) => {
      document.body.dataset["dragPointerId"] = String(event.pointerId);
    });
  });

  const card = page.locator(".task-card", { hasText: title });
  const cardBox = await card.boundingBox();
  if (!cardBox) throw new Error("Drag box is missing");
  await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(cardBox.x + cardBox.width / 2 + 16, cardBox.y + cardBox.height / 2 + 16, {
    steps: 4,
  });
  await expect(page.locator(".matrix-drag-ghost")).toBeVisible();

  const pointerId = await page.locator("body").getAttribute("data-drag-pointer-id");
  await page.evaluate((id) => {
    document.dispatchEvent(new PointerEvent("pointercancel", { pointerId: Number(id), bubbles: true }));
  }, pointerId);
  await page.mouse.up();

  await expect(page.locator(".matrix-drag-ghost")).toHaveCount(0);
  await expect(page.locator(".matrix-drag-placeholder")).toHaveCount(0);
});
test("keeps the matrix quadrant creation link working", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.getByRole("link", { name: "Create task in area 3" }).click({ position: { x: 5, y: 5 } });

  await expect(page).toHaveURL(/\/tasks\/new\?area=3/);
  await expect(page.locator("#new-task-meta .area-badge")).toHaveText("3");
});
test("navigates to New task from matrix padding and gap bands", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  for (const area of [1, 2, 3, 4]) {
    await expect(page.getByRole("link", { name: `Create task in area ${area}` })).toHaveCount(1);
  }

  async function axisPoint(fractionX: number, fractionY: number) {
    const box = await page.locator(".matrix-axis").boundingBox();
    if (!box) throw new Error("Matrix axis box is missing");
    return { x: box.x + box.width * fractionX, y: box.y + box.height * fractionY, box };
  }

  async function clickAxisPoint(fractionX: number, fractionY: number) {
    const point = await axisPoint(fractionX, fractionY);
    await page.mouse.click(point.x, point.y);
  }

  // Top padding band belongs to the top quadrants.
  await clickAxisPoint(0.25, 0.02);
  await expect(page).toHaveURL(/\/tasks\/new\?area=1&from=matrix/);
  await page.goto("/matrix");

  // Bottom padding band belongs to the bottom quadrants.
  await clickAxisPoint(0.75, 0.98);
  await expect(page).toHaveURL(/\/tasks\/new\?area=4&from=matrix/);
  await page.goto("/matrix");

  // Vertical gap band: left of the center line is area 1, right is area 2.
  const topGap = await axisPoint(0.5, 0.25);
  await page.mouse.click(topGap.x - 10, topGap.y);
  await expect(page).toHaveURL(/\/tasks\/new\?area=1&from=matrix/);
  await page.goto("/matrix");
  await page.mouse.click(topGap.x + 10, topGap.y);
  await expect(page).toHaveURL(/\/tasks\/new\?area=2&from=matrix/);
  await page.goto("/matrix");

  // Horizontal gap band: above the center line is area 1, below is area 3.
  const leftGap = await axisPoint(0.25, 0.5);
  await page.mouse.click(leftGap.x, leftGap.y - 10);
  await expect(page).toHaveURL(/\/tasks\/new\?area=1&from=matrix/);
  await page.goto("/matrix");
  await page.mouse.click(leftGap.x, leftGap.y + 10);
  await expect(page).toHaveURL(/\/tasks\/new\?area=3&from=matrix/);
  await page.goto("/matrix");

  // The axis intersection itself must not be a dead zone.
  await clickAxisPoint(0.5, 0.5);
  await expect(page).toHaveURL(/\/tasks\/new\?area=[1-4]&from=matrix/);
});
test("keeps matrix task card navigation working", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  const title = `E2E card ${Date.now()}`;
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.goto("/matrix");
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await page.locator(".task-card", { hasText: title }).click();

  await expect(page).toHaveURL(/\/tasks\/[^/]+\?from=matrix/);
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await waitForPageSettle(page);
  await expect(page.getByLabel("Title")).toHaveValue(title);
});
test("changes a Matrix task to done from the context menu", async ({ page }) => {
  await signIn(page);

  const title = `E2E context done ${Date.now()}`;
  await createMatrixTask(page, title);
  const card = page.locator(".task-card", { hasText: title });
  await card.click({ button: "right" });
  await page.locator('.matrix-menu [data-matrix-action="done"]').click();

  await expect(card).toHaveCount(0);
  await expectTaskVisibleInList(page, title, "done");
  await expect(page.locator(".task-row").filter({ hasText: title }).locator(".status--done")).toBeVisible();
});
test("changes a Matrix task to skip from the context menu", async ({ page }) => {
  await signIn(page);

  const title = `E2E context skip ${Date.now()}`;
  await createMatrixTask(page, title);
  const card = page.locator(".task-card", { hasText: title });
  await card.click({ button: "right" });
  await page.locator('.matrix-menu [data-matrix-action="skip"]').click();

  await expect(card).toHaveCount(0);
  await expectTaskVisibleInList(page, title, "skip");
  await expect(page.locator(".task-row").filter({ hasText: title }).locator(".status--skip")).toBeVisible();
});
test("shows the Matrix task action menu in delete, skip, done, working order", async ({ page }) => {
  const title = `E2E menu order ${Date.now()}`;
  await signIn(page);
  await createMatrixTask(page, title);

  const card = page.locator(".task-card", { hasText: title });
  await card.click({ button: "right" });
  const menu = page.locator(".matrix-menu");
  await expect(menu).toBeVisible();
  await expect(menu.locator("[data-matrix-action]")).toHaveText([
    "delete",
    "skip",
    "done",
    "working: off",
  ]);
});
test("toggles a Matrix task working state from the context menu", async ({ page }) => {
  await signIn(page);

  const title = `E2E context working ${Date.now()}`;
  await createMatrixTask(page, title);
  const card = page.locator(".task-card", { hasText: title });
  await card.click({ button: "right" });
  await page.locator('.matrix-menu [data-matrix-action="working"]').click();

  await expect(card).toHaveClass(/task-card--working/);
  await expect(card.locator(".working-badge")).toHaveText("working");

  await card.click({ button: "right" });
  await expect(page.locator('.matrix-menu [data-matrix-action="working"]')).toHaveText("working: on");
  await page.locator('.matrix-menu [data-matrix-action="working"]').click();

  await expect(card).not.toHaveClass(/task-card--working/);
  await expect(card.locator(".working-badge")).toHaveCount(0);
});
test("confirms Matrix task deletion in the centered dialog", async ({ page }) => {
  await signIn(page);

  const title = `E2E context delete ${Date.now()}`;
  await createMatrixTask(page, title);
  const card = page.locator(".task-card", { hasText: title });
  const taskId = await card.getAttribute("data-task-id");
  if (!taskId) throw new Error("Task ID is missing from the task card");
  const draftKey = `siftq.task-draft:${taskId}`;
  await page.evaluate(({ key }) => {
    localStorage.setItem(key, JSON.stringify({ title: "draft", description: "draft", updatedAt: Date.now() }));
  }, { key: draftKey });
  await card.click({ button: "right" });
  await page.locator('.matrix-menu [data-matrix-action="delete"]').click();

  const dialog = page.locator(".matrix-modal");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("このタスクを削除しますか？");
  await expect(page.locator(".matrix-modal-backdrop")).toBeVisible();
  await expect(page.locator(".matrix-menu")).toHaveCount(0);

  await dialog.locator('.matrix-modal-button[data-matrix-modal-action="cancel"]').click();
  await expect(dialog).toHaveCount(0);
  await expect(card).toBeVisible();

  await card.click({ button: "right" });
  await page.locator('.matrix-menu [data-matrix-action="delete"]').click();
  await page.locator('.matrix-modal-button[data-matrix-modal-action="confirm"]').click();
  await expect(card).toHaveCount(0);
  await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), draftKey)).toBeNull();

  await expectTaskAbsentFromList(page, title, "do");
});
