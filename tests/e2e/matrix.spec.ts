import type { Page } from "@playwright/test";
import { expect, installHtmxRoute, test } from "./fixtures";

const password = atob("dGVzdC1wYXNzd29yZA==");

test.describe.configure({ mode: "serial" });

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.waitForLoadState("domcontentloaded");
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
}

function descriptionEditor(page: Page) {
  return page.getByRole("textbox", { name: "Description" });
}

async function hasDraft(page: Page, title: string, description: string): Promise<boolean> {
  return page.evaluate(({ title, description }) => {
    for (let index = 0; index < localStorage.length; index += 1) {
      const value = localStorage.getItem(localStorage.key(index) ?? "");
      if (value !== null && value.includes(title) && value.includes(description)) return true;
    }
    return false;
  }, { title, description });
}

async function getTaskDraftKey(page: Page): Promise<string> {
  return page.locator('form[data-task-form="edit"]').evaluate((form) => {
    const match = (form.getAttribute("action") ?? "").match(/\/tasks\/([^/?#]+)/);
    const taskId = match?.[1];
    if (!taskId) throw new Error("Task ID is missing from the edit form action");
    return `siftq.task-draft:${decodeURIComponent(taskId)}`;
  });
}

async function expectDraftSaved(page: Page, title: string, description: string) {
  // The fake clock advances with real time, so keep a margin around the 500ms boundary.
  await page.clock.fastForward(400);
  expect(await hasDraft(page, title, description)).toBe(false);
  await page.clock.fastForward(200);
  expect(await hasDraft(page, title, description)).toBe(true);
}

async function expectDraftNotSaved(page: Page, title: string, description: string) {
  // New task drafts are disabled; wait past the save debounce and assert nothing is stored.
  await page.clock.fastForward(600);
  expect(await hasDraft(page, title, description)).toBe(false);
}

async function waitForPageSettle(page: Page) {
  // htmx swaps #page and settles (attaching submit handlers to the new form)
  // asynchronously; submitting before htmx:afterSettle falls back to a native
  // GET submit that stays on the form.
  await page.evaluate(() =>
    new Promise<void>((resolve) => {
      if (!document.querySelector(".htmx-settling")) {
        resolve();
        return;
      }
      document.addEventListener("htmx:afterSettle", () => resolve(), { once: true });
    }),
  );
}

async function disableLocalStorage(page: Page) {
  await page.evaluate(() => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      get() {
        throw new Error("localStorage is unavailable");
      },
    });
  });
}

async function createMatrixTask(page: Page, title: string) {
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
}

async function gotoListPage(page: Page, status: string) {
  const target = `/tasks?status=${status}`;
  // A save navigation can still be settling when the list assertion starts.
  // Wait before starting the next navigation to avoid Playwright cancelling it.
  await page.waitForLoadState("networkidle");
  try {
    await page.goto(target, { waitUntil: "networkidle" });
  } catch {
    await page.waitForLoadState("networkidle");
    await page.goto(target, { waitUntil: "networkidle" });
  }
}

async function expectTaskVisibleInList(page: Page, title: string, status: string) {
  await gotoListPage(page, status);
  for (let attempt = 0; attempt < 20; attempt += 1) {
    if ((await page.getByText(title, { exact: true }).count()) > 0) return;
    const next = page.getByRole("link", { name: "Next page" });
    if ((await next.count()) === 0) break;
    await next.click();
  }
  await expect(page.getByText(title, { exact: true })).toBeVisible();
}

async function openTaskFromList(page: Page, title: string, status: string) {
  await expectTaskVisibleInList(page, title, status);
  await page.getByText(title, { exact: true }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
}

async function expectTaskAbsentFromList(page: Page, title: string, status: string) {
  await gotoListPage(page, status);
  for (let attempt = 0; attempt < 20; attempt += 1) {
    await expect(page.getByText(title, { exact: true })).toHaveCount(0);
    const next = page.getByRole("link", { name: "Next page" });
    if ((await next.count()) === 0) return;
    await next.click();
  }
  await expect(page.getByText(title, { exact: true })).toHaveCount(0);
}

async function dismissPopover(page: Page, label: "status" | "area") {
  const title = label === "status" ? "Status" : "Area";
  const applyLabel = `Apply ${label} to this task`;

  await page.getByRole("link", { name: new RegExp(`^${title}`) }).click();
  const popover = page.locator(`[aria-label="${applyLabel}"]`);
  await expect(popover).toBeVisible();

  await page.getByLabel("Title").click();
  await expect(popover).toHaveCount(0);
}

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

    if (area < 4) await page.goto("/");
  }
});

test("keeps the page interactive after dragging and dropping a matrix card", async ({ page }) => {
  await signIn(page);

  const suffix = Date.now();
  const firstTitle = `E2E dnd first ${suffix}`;
  const secondTitle = `E2E dnd second ${suffix}`;
  await createMatrixTask(page, firstTitle);
  await createMatrixTask(page, secondTitle);
  await page.goto("/");
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
  await page.goto("/");
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
  await page.goto("/");
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
  await page.goto("/");
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

test("keeps matrix task card navigation working", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  const title = `E2E card ${Date.now()}`;
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await page.locator(".task-card", { hasText: title }).click();

  await expect(page).toHaveURL(/\/tasks\/[^/]+\?from=matrix/);
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
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

test("creates a task and sees it in the list", async ({ page }) => {
  const taskTitle = `E2E task ${Date.now()}`;

  await signIn(page);
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(taskTitle);
  await descriptionEditor(page).fill("created by Playwright");
  await page.getByRole("button", { name: "Create" }).click();

  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await expectTaskVisibleInList(page, taskTitle, "do");
});

test("creates a task when localStorage is unavailable", async ({ page }) => {
  const taskTitle = `E2E create without localStorage ${Date.now()}`;

  await signIn(page);
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").waitFor();
  await waitForPageSettle(page);
  await disableLocalStorage(page);
  await page.getByLabel("Title").fill(taskTitle);
  await descriptionEditor(page).fill("created without localStorage");
  await page.getByRole("button", { name: "Create" }).click();

  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await expectTaskVisibleInList(page, taskTitle, "do");
});

test("saves a task when localStorage is unavailable", async ({ page }) => {
  const originalTitle = `E2E save without localStorage ${Date.now()}`;
  const title = `${originalTitle} updated`;

  await signIn(page);
  await createMatrixTask(page, originalTitle);
  await page.locator(".task-card", { hasText: originalTitle }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await waitForPageSettle(page);
  await disableLocalStorage(page);
  await page.getByLabel("Title").fill(title);
  await descriptionEditor(page).fill("saved without localStorage");
  await page.getByRole("button", { name: "Save" }).click();

  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await expectTaskVisibleInList(page, title, "do");
});

test("does not save new task title and description as a local draft", async ({ page }) => {
  const title = `E2E new draft ${Date.now()}`;
  const description = "draft description for a new task";

  await signIn(page);
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").waitFor();
  await waitForPageSettle(page);
  await page.clock.install();
  await page.getByLabel("Title").fill(title);
  await descriptionEditor(page).fill(description);

  await expectDraftNotSaved(page, title, description);
});

test("saves task detail title and description as a local draft after input stops", async ({ page }) => {
  const originalTitle = `E2E detail draft ${Date.now()}`;
  const title = `${originalTitle} updated`;
  const description = "draft description for task detail";

  await signIn(page);
  await createMatrixTask(page, originalTitle);
  await page.locator(".task-card", { hasText: originalTitle }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await waitForPageSettle(page);
  await page.evaluate(() => localStorage.clear());
  await page.clock.install();

  await page.getByLabel("Title").fill(title);
  await descriptionEditor(page).fill(description);

  await expectDraftSaved(page, title, description);
});

test("deletes a task detail draft after a successful Save", async ({ page }) => {
  const originalTitle = `E2E save draft cleanup ${Date.now()}`;
  const title = `${originalTitle} updated`;
  const description = "draft removed after save";

  await signIn(page);
  await createMatrixTask(page, originalTitle);
  await page.locator(".task-card", { hasText: originalTitle }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await waitForPageSettle(page);
  const draftKey = await getTaskDraftKey(page);

  await page.evaluate(() => localStorage.clear());
  await page.clock.install();
  await page.getByLabel("Title").fill(title);
  await descriptionEditor(page).fill(description);
  await expectDraftSaved(page, title, description);

  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), draftKey)).toBeNull();
});

test("clears only the current browser profile drafts on logout", async ({ browser }) => {
  const currentContext = await browser.newContext({ baseURL: "http://127.0.0.1:4173" });
  const otherContext = await browser.newContext({ baseURL: "http://127.0.0.1:4173" });
  const currentPage = await currentContext.newPage();
  const otherPage = await otherContext.newPage();
  await installHtmxRoute(currentContext);
  await installHtmxRoute(otherContext);
  const draftKeys = ["siftq.task-draft:new", "siftq.task-draft:task-from-another-device"];
  const draftValue = JSON.stringify({ title: "draft", description: "draft", updatedAt: Date.now() });

  try {
    await signIn(currentPage);
    await otherPage.goto("/login");
    for (const page of [currentPage, otherPage]) {
      await page.evaluate(({ draftKeys, draftValue }) => {
        for (const key of draftKeys) localStorage.setItem(key, draftValue);
        localStorage.setItem("siftq.preference", "keep");
      }, { draftKeys, draftValue });
    }

    await currentPage.locator('form[action="/logout"] button[type="submit"]').click();
    await expect(currentPage).toHaveURL(/\/login$/);
    await expect.poll(() => currentPage.evaluate(() =>
      Object.keys(localStorage).filter((key) => key.startsWith("siftq.task-draft:")),
    )).toEqual([]);
    expect(await currentPage.evaluate(() => localStorage.getItem("siftq.preference"))).toBe("keep");
    expect(await otherPage.evaluate(() =>
      Object.keys(localStorage).filter((key) => key.startsWith("siftq.task-draft:")).sort(),
    )).toEqual(draftKeys.sort());
  } finally {
    await Promise.all([currentContext.close(), otherContext.close()]);
  }
});

test("does not keep a new task draft after a failed Create request", async ({ page }) => {
  const title = `E2E failed create draft ${Date.now()}`;
  const description = "draft retained after communication failure";

  await signIn(page);
  await page.route("**/tasks", async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    await route.abort("failed");
  });
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").waitFor();
  await waitForPageSettle(page);
  await page.clock.install();
  await page.getByLabel("Title").fill(title);
  await descriptionEditor(page).fill(description);
  await expectDraftNotSaved(page, title, description);

  const requestFailed = page.waitForEvent("requestfailed", {
    predicate: (request) => request.method() === "POST" && request.url().endsWith("/tasks"),
  });
  await page.getByRole("button", { name: "Create" }).click();
  await requestFailed;
  await expect(page.getByRole("heading", { name: "New task" })).toBeVisible();
  await expect(page.getByLabel("Title")).toHaveValue(title);
  await expect.poll(() => hasDraft(page, title, description)).toBe(false);
});

test("keeps a task detail draft after an input error", async ({ page }) => {
  const originalTitle = `E2E invalid input ${Date.now()}`;
  const title = `${originalTitle} updated`;
  const description = "draft retained after input error";

  await signIn(page);
  await createMatrixTask(page, originalTitle);
  await page.locator(".task-card", { hasText: originalTitle }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await waitForPageSettle(page);
  const draftKey = await getTaskDraftKey(page);
  await page.evaluate(() => localStorage.clear());
  await page.clock.install();
  await page.getByLabel("Title").fill(title);
  await descriptionEditor(page).fill(description);
  await expectDraftSaved(page, title, description);

  await page.locator("#task-version").evaluate((input) => input.remove());
  const responsePromise = page.waitForResponse(
    (response) => response.request().method() === "POST" && response.url().includes("/tasks/"),
  );
  await page.getByRole("button", { name: "Save" }).click();
  expect((await responsePromise).status()).toBe(400);
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), draftKey)).toContain(title);
});

test("does not restore a saved new task draft on initial page load", async ({ page }) => {
  const title = `E2E restored new draft ${Date.now()}`;
  const description = "restored new task description";

  await signIn(page);
  await page.evaluate(({ title, description }) => {
    localStorage.setItem("siftq.task-draft:new", JSON.stringify({ title, description, updatedAt: Date.now() }));
  }, { title, description });
  await page.goto("/tasks/new?from=tasks");

  await expect(page.getByLabel("Title")).toHaveValue("");
  await expect(descriptionEditor(page)).toHaveText("");
  await expect(page.locator('textarea[data-description-value]')).toHaveValue("");
});

test("does not restore a saved new task draft after an HTMX navigation", async ({ page }) => {
  const title = `E2E restored HTMX draft ${Date.now()}`;
  const description = "restored after HTMX navigation";

  await signIn(page);
  await page.evaluate(({ title, description }) => {
    localStorage.setItem("siftq.task-draft:new", JSON.stringify({ title, description, updatedAt: Date.now() }));
  }, { title, description });
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").waitFor();
  await waitForPageSettle(page);

  await expect(page.getByLabel("Title")).toHaveValue("");
  await expect(descriptionEditor(page)).toHaveText("");
  await expect(page.locator('textarea[data-description-value]')).toHaveValue("");
});

test("restores a task detail draft for its task ID", async ({ page }) => {
  const originalTitle = `E2E restored detail ${Date.now()}`;
  const title = `${originalTitle} updated`;
  const description = "restored task detail description";

  await signIn(page);
  await createMatrixTask(page, originalTitle);
  await page.locator(".task-card", { hasText: originalTitle }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await waitForPageSettle(page);

  const draftKey = await getTaskDraftKey(page);
  const version = Number(await page.locator("#task-version").inputValue());
  await page.evaluate(({ key, title, description, version }) => {
    localStorage.setItem(key, JSON.stringify({ title, description, version, updatedAt: Date.now() }));
  }, { key: draftKey, title, description, version });
  await page.reload();

  await expect(page.getByLabel("Title")).toHaveValue(title);
  await expect(descriptionEditor(page)).toHaveText(description);
  await expect(page.locator('textarea[data-description-value]')).toHaveValue(description);
});

test("restores the last saved task draft across multiple tabs", async ({ page }) => {
  const originalTitle = `E2E multi-tab draft ${Date.now()}`;
  const firstTitle = `${originalTitle} first`;
  const firstDescription = "first tab draft";
  const lastTitle = `${originalTitle} last`;
  const lastDescription = "last tab draft";

  await signIn(page);
  await createMatrixTask(page, originalTitle);
  await page.locator(".task-card", { hasText: originalTitle }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await waitForPageSettle(page);

  const draftKey = await getTaskDraftKey(page);
  const secondPage = await page.context().newPage();
  try {
    await secondPage.goto(page.url());
    await expect(secondPage.getByRole("heading", { name: "Task detail" })).toBeVisible();
    await waitForPageSettle(secondPage);
    await page.evaluate(() => localStorage.clear());

    await page.getByLabel("Title").fill(firstTitle);
    await descriptionEditor(page).fill(firstDescription);
    await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), draftKey)).toContain(firstTitle);

    await secondPage.getByLabel("Title").fill(lastTitle);
    await descriptionEditor(secondPage).fill(lastDescription);
    await expect
      .poll(() => secondPage.evaluate((key) => localStorage.getItem(key), draftKey))
      .toContain(lastTitle);
    expect(await page.evaluate((key) => localStorage.getItem(key), draftKey)).not.toContain(firstTitle);

    await page.reload();
    await expect(page.getByLabel("Title")).toHaveValue(lastTitle);
    await expect(descriptionEditor(page)).toHaveText(lastDescription);
    await expect(page.locator('textarea[data-description-value]')).toHaveValue(lastDescription);
  } finally {
    await secondPage.close();
  }
});

test("discards a task detail draft when its base version is stale", async ({ page }) => {
  const serverTitle = `E2E server task ${Date.now()}`;
  const serverDescription = "server description remains authoritative";
  const draftTitle = `${serverTitle} stale draft`;
  const draftDescription = "stale draft description";

  await signIn(page);
  await page.goto("/tasks/new");
  await page.getByLabel("Title").fill(serverTitle);
  await descriptionEditor(page).fill(serverDescription);
  await page.getByRole("button", { name: "Create" }).click();
  await openTaskFromList(page, serverTitle, "do");

  const draftKey = await getTaskDraftKey(page);
  const serverVersion = Number(await page.locator("#task-version").inputValue());
  await page.evaluate(({ key, title, description, version }) => {
    localStorage.setItem(key, JSON.stringify({
      title,
      description,
      version: version + 1,
      updatedAt: Date.now(),
    }));
  }, { key: draftKey, title: draftTitle, description: draftDescription, version: serverVersion });
  await page.reload();

  await expect(page.getByLabel("Title")).toHaveValue(serverTitle);
  await expect(descriptionEditor(page)).toHaveText(serverDescription);
  await expect(page.locator('textarea[data-description-value]')).toHaveValue(serverDescription);
  await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), draftKey)).toBeNull();
});

test("discards a stale task detail draft after an HTMX navigation", async ({ page }) => {
  const serverTitle = `E2E htmx stale ${Date.now()}`;
  const serverDescription = "server description remains authoritative via HTMX";
  const draftTitle = `${serverTitle} stale draft`;
  const draftDescription = "stale draft description via HTMX";

  await signIn(page);
  await page.goto("/tasks/new");
  await page.getByLabel("Title").fill(serverTitle);
  await descriptionEditor(page).fill(serverDescription);
  await page.getByRole("button", { name: "Create" }).click();
  await openTaskFromList(page, serverTitle, "do");

  const draftKey = await getTaskDraftKey(page);
  const serverVersion = Number(await page.locator("#task-version").inputValue());
  const detailUrl = page.url();
  await page.evaluate(({ key, title, description, version }) => {
    localStorage.setItem(key, JSON.stringify({
      title,
      description,
      version: version + 1,
      updatedAt: Date.now(),
    }));
  }, { key: draftKey, title: draftTitle, description: draftDescription, version: serverVersion });

  // HTMX navigation re-renders the edit form via swap; restoration (htmx:load)
  // must run before the version refresh (htmx:afterSettle) so the stale draft
  // is discarded instead of being re-based onto the new server version.
  await page.evaluate(
    `htmx.ajax("GET", ${JSON.stringify(detailUrl)}, { target: "#page", swap: "innerHTML" })`,
  );
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await waitForPageSettle(page);

  await expect(page.getByLabel("Title")).toHaveValue(serverTitle);
  await expect(descriptionEditor(page)).toHaveText(serverDescription);
  await expect(page.locator('textarea[data-description-value]')).toHaveValue(serverDescription);
  await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), draftKey)).toBeNull();
});

test("ignores an invalid saved task draft", async ({ page }) => {
  const title = `E2E invalid draft ${Date.now()}`;

  await signIn(page);
  await createMatrixTask(page, title);
  await page.locator(".task-card", { hasText: title }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await waitForPageSettle(page);
  const draftKey = await getTaskDraftKey(page);
  await page.evaluate((key) => localStorage.setItem(key, "not-json"), draftKey);
  await page.reload();

  await expect(page.getByLabel("Title")).toHaveValue(title);
});

test("continues normally when localStorage draft reading fails", async ({ page }) => {
  const pageErrors: Error[] = [];
  page.on("pageerror", (error) => pageErrors.push(error));

  const title = `E2E storage failure ${Date.now()}`;
  await signIn(page);
  await createMatrixTask(page, title);
  await page.locator(".task-card", { hasText: title }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await waitForPageSettle(page);
  const detailUrl = page.url();

  await page.addInitScript(() => {
    Object.defineProperty(Storage.prototype, "getItem", {
      configurable: true,
      value: () => {
        throw new Error("localStorage is unavailable");
      },
    });
  });
  await page.goto(detailUrl);
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();

  await expect(page.getByLabel("Title")).toHaveValue(title);
  expect(pageErrors).toHaveLength(0);
});

test("opens description URLs with native link behavior", async ({ page }) => {
  const taskTitle = `E2E description links ${Date.now()}`;
  const taskUrl = "http://127.0.0.1:4173/tasks";

  await signIn(page);
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(taskTitle);
  await descriptionEditor(page).fill(`Open ${taskUrl} or ${taskUrl}`);
  await page.getByRole("button", { name: "Create" }).click();

  await page.locator(".task-card", { hasText: taskTitle }).click();
  const links = descriptionEditor(page).locator("a");
  await expect(links).toHaveCount(2);
  await expect(links.first()).toHaveAttribute("href", taskUrl);

  const popupPromise = page.waitForEvent("popup");
  await links.nth(1).click({ modifiers: ["Control"] });
  const popup = await popupPromise;
  await expect(popup).toHaveURL(/\/tasks$/);
  await popup.close();

  await links.first().click();
  await expect(page).toHaveURL(/\/tasks$/);
});

test("linkifies pasted URLs and submits plain text", async ({ page }) => {
  const taskTitle = `E2E pasted description URL ${Date.now()}`;
  const taskUrl = "http://127.0.0.1:4173/tasks";
  const description = `Pasted ${taskUrl}`;

  await signIn(page);
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(taskTitle);

  const editor = descriptionEditor(page);
  await editor.click();
  await editor.evaluate((element, text) => {
    const range = document.createRange();
    range.selectNodeContents(element);
    range.collapse(false);
    const selection = window.getSelection();
    if (!selection) throw new Error("Selection is unavailable");
    selection.removeAllRanges();
    selection.addRange(range);
    const data = new DataTransfer();
    data.setData("text/plain", text);
    element.dispatchEvent(new ClipboardEvent("paste", { bubbles: true, clipboardData: data }));
  }, description);

  await expect(editor.locator("a")).toHaveAttribute("href", taskUrl);
  await page.getByRole("button", { name: "Create" }).click();
  await page.locator(".task-card", { hasText: taskTitle }).click();

  await expect(descriptionEditor(page).locator("a")).toHaveAttribute("href", taskUrl);
  await expect(page.locator('textarea[data-description-value]')).toHaveValue(description);
});

test("deletes text before a description URL at the URL boundary", async ({ page }) => {
  const taskTitle = `E2E description URL backspace ${Date.now()}`;
  const taskUrl = "https://example.com/tasks";
  const description = `Before ${taskUrl}`;
  const expectedDescription = `Before${taskUrl}`;

  await signIn(page);
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(taskTitle);
  await descriptionEditor(page).fill(description);
  await page.getByRole("button", { name: "Create" }).click();

  await page.locator(".task-card", { hasText: taskTitle }).click();
  const editor = descriptionEditor(page);
  const urlLink = editor.locator("a", { hasText: taskUrl });
  await expect(urlLink).toHaveCount(1);
  await urlLink.evaluate((element) => {
    const editor = element.closest("[data-description-editor]");
    if (!(editor instanceof HTMLElement)) throw new Error("Description editor is unavailable");
    editor.focus();

    const range = document.createRange();
    range.setStartBefore(element);
    range.collapse(true);
    const selection = window.getSelection();
    if (!selection) throw new Error("Selection is unavailable");
    selection.removeAllRanges();
    selection.addRange(range);
  });

  await page.keyboard.press("Backspace");

  await expect(editor).toHaveText(expectedDescription);
  await expect(page.locator('textarea[data-description-value]')).toHaveValue(expectedDescription);
});

test("creates exactly one task with Ctrl+Enter from the title or description", async ({ page }) => {
  await signIn(page);

  for (const field of ["Title", "Description"] as const) {
    const taskTitle = `E2E shortcut ${field} ${Date.now()}`;
    await page.getByRole("link", { name: "New task" }).click();
    // click() does not wait for the htmx swap; waitForURL alone can resolve
    // before the form is settled (see waitForPageSettle).
    await page.waitForURL(/\/tasks\/new/);
    await page.getByLabel("Title").waitFor();
    await waitForPageSettle(page);
    await page.getByLabel("Title").fill(taskTitle);
    if (field === "Description") await descriptionEditor(page).fill("created by shortcut");
    await (field === "Description" ? descriptionEditor(page) : page.getByLabel(field)).press("Control+Enter");

    await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
    await expect(page.locator(".task-card", { hasText: taskTitle })).toHaveCount(1);
  }
});

test("saves exactly one task with Ctrl+Enter from the detail form", async ({ page }) => {
  const originalTitle = `E2E detail shortcut ${Date.now()}`;
  const updatedTitle = `${originalTitle} updated`;

  await signIn(page);
  await createMatrixTask(page, originalTitle);
  await page.locator(".task-card", { hasText: originalTitle }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();

  await page.getByLabel("Title").fill(updatedTitle);
  await descriptionEditor(page).press("Control+Enter");

  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await expect(page.locator(".task-card", { hasText: updatedTitle })).toHaveCount(1);
});

test("refreshes task detail after browser back before Ctrl+Enter and Save", async ({ page }) => {
  const originalTitle = `E2E browser back ${Date.now()}`;
  const shortcutTitle = `${originalTitle} shortcut`;
  const resavedTitle = `${shortcutTitle} resaved`;
  const saveTitle = `${resavedTitle} saved`;
  const conflictResponses: string[] = [];

  await signIn(page);
  page.on("response", (response) => {
    if (response.status() === 409) conflictResponses.push(response.url());
  });

  await createMatrixTask(page, originalTitle);
  await page.locator(".task-card", { hasText: originalTitle }).click();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  const initialVersion = await page.locator("#task-version").inputValue();

  await page.getByLabel("Title").fill(shortcutTitle);
  await page.getByLabel("Title").press("Control+Enter");
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.goBack();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await expect(page.getByLabel("Title")).toHaveValue(shortcutTitle);
  await expect(page.locator("#task-version")).not.toHaveValue(initialVersion);
  const shortcutVersion = await page.locator("#task-version").inputValue();

  await page.getByLabel("Title").fill(resavedTitle);
  await page.getByLabel("Title").press("Control+Enter");
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await expect(page.locator(".task-card", { hasText: resavedTitle })).toHaveCount(1);

  await page.goBack();
  await expect(page.getByRole("heading", { name: "Task detail" })).toBeVisible();
  await expect(page.getByLabel("Title")).toHaveValue(resavedTitle);
  await expect(page.locator("#task-version")).not.toHaveValue(shortcutVersion);

  await page.getByLabel("Title").fill(saveTitle);
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await expect(page.locator(".task-card", { hasText: saveTitle })).toHaveCount(1);
  expect(conflictResponses).toHaveLength(0);
});

test("keeps native task validation on Ctrl+Enter", async ({ page }) => {
  await signIn(page);
  await page.getByRole("link", { name: "New task" }).click();
  await descriptionEditor(page).fill("description without a title");
  await descriptionEditor(page).press("Control+Enter");

  await expect(page.getByRole("heading", { name: "New task" })).toBeVisible();
  const titleIsInvalid = await page.getByLabel("Title").evaluate(
    (element) => element instanceof HTMLInputElement && !element.validity.valid,
  );
  expect(titleIsInvalid).toBe(true);
});

test("creates a task from the task list and returns to the task list", async ({ page }) => {
  const taskTitle = `E2E list task ${Date.now()}`;

  await signIn(page);
  await page.goto("/tasks");
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").fill(taskTitle);
  await page.getByRole("button", { name: "Create" }).click();

  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
  await expectTaskVisibleInList(page, taskTitle, "do");
});

test("filters the task list by status and retains it after reload", async ({ page }) => {
  await signIn(page);

  const suffix = Date.now();
  for (const status of ["do", "done", "skip"] as const) {
    const title = `E2E filter ${status} ${suffix}`;
    await page.goto(`/tasks/new?status=${status}`);
    await page.getByLabel("Title").fill(title);
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
  }

  await page.goto("/tasks");
  await expect(page.getByText(`E2E filter done ${suffix}`, { exact: true })).not.toBeVisible();
  await expect(page.getByText(`E2E filter skip ${suffix}`, { exact: true })).not.toBeVisible();
  await expectTaskVisibleInList(page, `E2E filter do ${suffix}`, "do");

  await page.locator('a[href="/tasks?status=done"]').click();
  await expect(page).toHaveURL(/\/tasks\?status=done$/);
  await expectTaskVisibleInList(page, `E2E filter done ${suffix}`, "done");

  await page.reload();
  await expect(page).toHaveURL(/\/tasks\?status=done$/);
  await expectTaskVisibleInList(page, `E2E filter done ${suffix}`, "done");

  await page.goto("/");
  await page.locator('nav.nav a[href="/tasks"]').click();
  await expect(page).toHaveURL(/\/tasks$/);
  await expect(page.locator('a[href="/tasks?status=do"][aria-current="true"]')).toBeVisible();
  await expectTaskVisibleInList(page, `E2E filter do ${suffix}`, "do");
});

test("keeps new-task inputs while changing Status and Area", async ({ page }) => {
  const title = `Retained title ${Date.now()}`;
  await signIn(page);

  await page.goto("/tasks/new");
  await page.getByLabel("Title").fill(title);
  await descriptionEditor(page).fill("Retained description");

  await page.locator("#new-task-meta details").first().locator("summary").click();
  await page.locator('input[name="status"][value="done"]').check();
  await expect(page.getByLabel("Title")).toHaveValue(title);
  await expect(descriptionEditor(page)).toHaveText("Retained description");

  await page.locator("#new-task-meta details").nth(1).locator("summary").click();
  await page.locator('input[name="area"][value="4"]').check();
  await expect(page.getByLabel("Title")).toHaveValue(title);
  await expect(descriptionEditor(page)).toHaveText("Retained description");

  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
  await expectTaskVisibleInList(page, title, "done");
  await page.getByText(title, { exact: true }).click();
  await expect(page.locator("#task-meta .status--done")).toHaveText("done");
  await expect(page.locator("#task-meta .area-badge")).toHaveText("4");
});

test("dismisses new task Status popover when clicking outside", async ({ page }) => {
  await signIn(page);
  await page.goto("/tasks/new");

  const statusDetails = page.locator("#new-task-meta details").first();
  await statusDetails.locator("summary").click();
  const popover = page.locator('[aria-label="Apply status to this task"]');
  await expect(popover).toBeVisible();

  await page.getByLabel("Title").click();
  await expect(statusDetails).not.toHaveAttribute("open");
  await expect(popover).toBeHidden();
});

test("dismisses new task Area popover when clicking outside", async ({ page }) => {
  await signIn(page);
  await page.goto("/tasks/new");

  const areaDetails = page.locator("#new-task-meta details").nth(1);
  await areaDetails.locator("summary").click();
  const popover = page.locator('[aria-label="Apply area to this task"]');
  await expect(popover).toBeVisible();

  await page.getByLabel("Title").click();
  await expect(areaDetails).not.toHaveAttribute("open");
  await expect(popover).toBeHidden();
});

test("closes new task Status and Area popovers with Cancel without changing selection", async ({
  page,
}) => {
  await signIn(page);
  await page.goto("/tasks/new");

  const statusDetails = page.locator("#new-task-meta details").first();
  await statusDetails.locator("summary").click();
  await page
    .locator('[aria-label="Apply status to this task"] [data-popover-cancel]')
    .click();
  await expect(statusDetails).not.toHaveAttribute("open");
  await expect(page.locator('input[name="status"][value="do"]')).toBeChecked();

  const areaDetails = page.locator("#new-task-meta details").nth(1);
  await areaDetails.locator("summary").click();
  await page.locator('[aria-label="Apply area to this task"] [data-popover-cancel]').click();
  await expect(areaDetails).not.toHaveAttribute("open");
  await expect(page.locator('input[name="area"][value="1"]')).toBeChecked();
});

test("closes new task popover when selecting a choice", async ({ page }) => {
  await signIn(page);
  await page.goto("/tasks/new");

  const statusDetails = page.locator("#new-task-meta details").first();
  await statusDetails.locator("summary").click();
  await page.locator('input[name="status"][value="done"]').check();
  await expect(statusDetails).not.toHaveAttribute("open");
});

test("dismisses task detail Status and Area popovers when clicking outside", async ({ page }) => {
  await signIn(page);

  const title = `E2E popover task ${Date.now()}`;
  await page.goto("/tasks/new?status=do&area=2");
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
  await openTaskFromList(page, title, "do");

  await dismissPopover(page, "status");
  await expect(page.locator("#task-meta .status--do")).toHaveText("do");

  await dismissPopover(page, "area");
  await expect(page.locator("#task-meta .area-badge")).toHaveText("2");
});

async function saveAfterMetaChange(page: Page, kind: "status" | "area", value: string) {
  const title = `E2E ${kind} save ${Date.now()}`;
  const description = `E2E ${kind} draft`;

  await page.goto("/tasks/new");
  await page.getByLabel("Title").fill(title);
  await descriptionEditor(page).fill(description);
  await page.getByRole("button", { name: "Create" }).click();
  await openTaskFromList(page, title, "do");

  const draftTitle = `${title} saved`;
  const draftKey = await getTaskDraftKey(page);
  await page.evaluate(() => localStorage.clear());
  await page.clock.install();
  await page.getByLabel("Title").fill(draftTitle);
  await descriptionEditor(page).fill(description);
  await expectDraftSaved(page, draftTitle, description);

  const version = page.locator("#task-version");
  const beforeMetaChange = await version.inputValue();
  await page.getByRole("link", { name: new RegExp(`^${kind === "status" ? "Status" : "Area"}`) }).click();
  await page.locator(`[aria-label="Apply ${kind} to this task"] .status-choice`, { hasText: value }).click();
  await expect(version).not.toHaveValue(beforeMetaChange);
  await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), draftKey)).toContain(draftTitle);
  await page.getByRole("button", { name: "Save" }).click();

  await expect(page).toHaveURL(/\/tasks$/);
  await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), draftKey)).toBeNull();
  if (kind === "status") {
    await expectTaskVisibleInList(page, draftTitle, value);
  } else {
    await expectTaskVisibleInList(page, draftTitle, "do");
  }
}

test("saves after changing task status", async ({ page }) => {
  await signIn(page);

  await saveAfterMetaChange(page, "status", "done");
});

test("saves after changing task area", async ({ page }) => {
  await signIn(page);

  await saveAfterMetaChange(page, "area", "4");
});

test("persists an edit and displays a conflict from a stale editor", async ({ page }) => {
  await signIn(page);

  const title = `E2E concurrent task ${Date.now()}`;
  await page.goto("/tasks/new?status=do&area=2");
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
  await openTaskFromList(page, title, "do");

  const staleEditor = await page.context().newPage();
  await staleEditor.goto(page.url());
  await expect(staleEditor.getByLabel("Title")).toHaveValue(title);

  await page.getByLabel("Title").fill("E2E saved task");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page).toHaveURL(/\/tasks$/);
  await expectTaskVisibleInList(page, "E2E saved task", "do");

  const staleTitle = "E2E stale task";
  const staleDescription = "draft retained after conflict";
  await staleEditor.clock.install();
  await staleEditor.getByLabel("Title").fill(staleTitle);
  await descriptionEditor(staleEditor).fill(staleDescription);
  await expectDraftSaved(staleEditor, staleTitle, staleDescription);
  await staleEditor.getByRole("button", { name: "Save" }).click();
  await expect(staleEditor.getByText("Task was updated elsewhere.")).toBeVisible();
  await expect(staleEditor.getByRole("link", { name: "Load latest" })).toBeVisible();
  await expect.poll(() => hasDraft(staleEditor, staleTitle, staleDescription)).toBe(true);
});

test("does not keep a new task draft when cancelling from the matrix", async ({ page }) => {
  const title = `E2E cancel draft ${Date.now()}`;
  const description = "draft retained after cancel";

  await signIn(page);
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();

  await page.getByRole("link", { name: "New task" }).click();
  await expect(page.getByRole("heading", { name: "New task" })).toBeVisible();
  await page.getByLabel("Title").waitFor();
  await waitForPageSettle(page);
  await page.clock.install();
  await page.getByLabel("Title").fill(title);
  await descriptionEditor(page).fill(description);
  await expectDraftNotSaved(page, title, description);

  await page.getByRole("link", { name: "Cancel", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await expect.poll(() => hasDraft(page, title, description)).toBe(false);

  await page.getByRole("link", { name: "New task" }).click();
  await expect(page.getByLabel("Title")).toHaveValue("");
  await expect(descriptionEditor(page)).toHaveText("");
});

test("cancels a new task from the task list and returns to the task list", async ({ page }) => {
  await signIn(page);
  await page.goto("/tasks");
  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();

  await page.getByRole("link", { name: "New task" }).click();
  await expect(page.getByRole("heading", { name: "New task" })).toBeVisible();

  await page.getByRole("link", { name: "Cancel", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();
});

test("does not keep a new task draft when navigating to another screen", async ({ page }) => {
  const title = `E2E navigation draft ${Date.now()}`;
  const description = "draft retained after navigation";

  await signIn(page);
  await page.getByRole("link", { name: "New task" }).click();
  await page.getByLabel("Title").waitFor();
  await waitForPageSettle(page);
  await page.clock.install();
  await page.getByLabel("Title").fill(title);
  await descriptionEditor(page).fill(description);
  await expectDraftNotSaved(page, title, description);

  await page.locator('nav.nav a[href="/"]').click();
  await expect(page.getByRole("heading", { name: "Matrix" })).toBeVisible();
  await expect.poll(() => hasDraft(page, title, description)).toBe(false);

  await page.getByRole("link", { name: "New task" }).click();
  await expect(page.getByLabel("Title")).toHaveValue("");
  await expect(descriptionEditor(page)).toHaveText("");
});
