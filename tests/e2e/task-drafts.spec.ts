import { signIn, descriptionEditor, hasDraft, getTaskDraftKey, expectDraftSaved, expectDraftNotSaved, waitForPageSettle, disableLocalStorage, createMatrixTask, expectTaskVisibleInList, openTaskFromList } from "./matrix-helpers";
import { authStatePath, e2eBaseUrl, expect, installHtmxRoute, test } from "./fixtures";

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

  await expect(page.getByLabel("Title")).toHaveValue(title);
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
  const currentContext = await browser.newContext({ baseURL: e2eBaseUrl, storageState: authStatePath });
  const otherContext = await browser.newContext({ baseURL: e2eBaseUrl });
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
