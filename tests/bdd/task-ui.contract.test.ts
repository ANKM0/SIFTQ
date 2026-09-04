import { beforeEach, describe, expect, it } from "vite-plus/test";
import { authenticatedRequest } from "../helpers/authenticated-request";
import { taskFixture } from "../helpers/task-fixture";
import { MemoryTaskRepository } from "../helpers/memory-task-repository";

let repo: MemoryTaskRepository;

beforeEach(() => {
  repo = new MemoryTaskRepository();
});

function request(path: string, init?: RequestInit) {
  return authenticatedRequest(path, repo, init);
}

function cardIds(body: string): string[] {
  const ids: string[] = [];
  for (const match of body.matchAll(/data-task-id="([^"]+)"/g)) {
    const id = match[1];
    if (id !== undefined) ids.push(id);
  }
  return ids;
}

function cardIdsInArea(body: string, area: number): string[] {
  const section = body.match(new RegExp(`<section[^>]*data-drop-area="${area}"[\\s\\S]*?</section>`))?.[0] ?? "";
  return cardIds(section);
}

function cardOpeningTag(body: string, id: string): string {
  return body.match(new RegExp(`<a[^>]*data-task-id="${id}"[^>]*>`))?.[0] ?? "";
}

describe("Matrix page", () => {
  it("renders the full page and an HTMX fragment", async () => {
    await repo.insert(taskFixture({ id: "task-1", status: "do", area: 1 }));

    const full = await request("/");
    const fullBody = await full.text();
    expect(full.status).toBe(200);
    expect(fullBody).toContain("<html");
    expect(fullBody).toContain("Matrix");
    expect(fullBody).toContain('data-task-id="task-1"');

    const fragment = await request("/", {
      headers: { "HX-Request": "true" },
    });
    const fragmentBody = await fragment.text();
    expect(fragment.status).toBe(200);
    expect(fragmentBody).not.toContain("<html");
    expect(fragmentBody).toContain("Matrix");
  });

  it("renders four quadrants with area creation links and compact status cards", async () => {
    await repo.insert(taskFixture({ id: "task-1", status: "do", area: 1 }));

    const body = await (await request("/")).text();

    expect(body).toContain('class="area area--quadrant area--q1"');
    expect(body).toContain('class="area area--quadrant area--q4"');
    expect(body).toContain("axis-line--horizontal");
    expect(body).toContain("axis-line--vertical");
    expect(body).toContain('data-task-id="task-1"');
    expect(body).toContain('href="/tasks/new?area=1&amp;from=matrix"');
    expect(body).toContain('href="/tasks/task-1?from=matrix"');
    expect(body).toContain("status--do");
  });
});

describe("Matrix area display sort", () => {
  it("sorts area cards by title when ?sort=title", async () => {
    await repo.insert(taskFixture({ id: "z", title: "Zebra", area: 1, order: 0 }));
    await repo.insert(taskFixture({ id: "a", title: "Apple", area: 1, order: 1 }));
    await repo.insert(taskFixture({ id: "m", title: "Mango", area: 1, order: 2 }));

    const body = await (await request("/?sort=title")).text();

    expect(cardIds(body)).toEqual(["a", "m", "z"]);
  });

  it("keeps order as the default sort", async () => {
    await repo.insert(taskFixture({ id: "z", title: "Zebra", area: 1, order: 0 }));
    await repo.insert(taskFixture({ id: "a", title: "Apple", area: 1, order: 1 }));

    const body = await (await request("/")).text();

    expect(cardIds(body)).toEqual(["z", "a"]);
  });

  it("falls back to order sort for an unknown sort key", async () => {
    await repo.insert(taskFixture({ id: "z", title: "Zebra", area: 1, order: 0 }));
    await repo.insert(taskFixture({ id: "a", title: "Apple", area: 1, order: 1 }));

    const body = await (await request("/?sort=status")).text();

    expect(cardIds(body)).toEqual(["z", "a"]);
  });

  it("keeps sorted cards in their original area and preserves card actions", async () => {
    await repo.insert(taskFixture({ id: "b", title: "Banana", area: 2, order: 0 }));
    await repo.insert(taskFixture({ id: "z", title: "Zebra", area: 1, order: 0 }));
    await repo.insert(taskFixture({ id: "a", title: "Apple", area: 1, order: 1 }));

    const body = await (await request("/?sort=title")).text();

    expect(cardIds(body)).toEqual(["a", "z", "b"]);
    expect(cardIdsInArea(body, 1)).toEqual(["a", "z"]);
    expect(cardIdsInArea(body, 2)).toEqual(["b"]);
    expect(body).toContain('src="/matrix-dnd.js"');
    expect(body).toContain('data-dnd-group="matrix"');
    for (const id of ["a", "z", "b"]) {
      const card = cardOpeningTag(body, id);
      expect(card).toContain(`draggable="true"`);
      expect(card).toContain(`href="/tasks/${id}?from=matrix"`);
    }
  });

  it("keeps sort controls on their own row with many cards so they do not overlap the Matrix", async () => {
    for (let i = 0; i < 20; i += 1) {
      await repo.insert(
        taskFixture({ id: `t${i}`, title: `Task ${String(19 - i).padStart(2, "0")}`, area: 1, order: i }),
      );
    }

    const body = await (await request("/?sort=title")).text();
    const sortIndex = body.indexOf('class="matrix-sort"');
    const matrixIndex = body.indexOf('class="matrix matrix-axis"');

    expect(sortIndex).toBeGreaterThan(-1);
    expect(matrixIndex).toBeGreaterThan(sortIndex);
    expect(cardIdsInArea(body, 1)).toHaveLength(20);
    expect(cardIdsInArea(body, 1)[0]).toBe("t19");
    const firstCard = cardOpeningTag(body, "t19");
    expect(firstCard).toContain('draggable="true"');
    expect(firstCard).toContain('href="/tasks/t19?from=matrix"');
  });
});

describe("Task list page", () => {
  it("renders all statuses", async () => {
    await repo.insert(taskFixture({ id: "done-1", status: "done" }));
    await repo.insert(taskFixture({ id: "skip-1", status: "skip" }));

    const response = await request("/tasks");
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain("done-1");
    expect(body).toContain("skip-1");
  });

  it("renders compact issues-like rows with area and status badges", async () => {
    await repo.insert(taskFixture({ id: "task-1", status: "do", area: 2 }));

    const body = await (await request("/tasks")).text();

    expect(body).toContain('class="task-row"');
    expect(body).toContain("#1");
    expect(body).toContain("seed task");
    expect(body).toContain("status area-badge");
    expect(body).toContain("status--do");
  });
});

describe("Task creation", () => {
  it("redirects to the task list after creating a task by default", async () => {
    const response = await request("/tasks", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ title: "Buy milk", description: "low-fat" }).toString(),
    });
    expect(response.status).toBe(201);
    expect(response.headers.get("hx-redirect")).toBe("/tasks");
    expect(await response.text()).toBe("");
  });

  it("redirects to the matrix after creating a task from the matrix", async () => {
    const response = await request("/tasks", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ title: "Buy milk", from: "matrix" }).toString(),
    });

    expect(response.status).toBe(201);
    expect(response.headers.get("hx-redirect")).toBe("/");

    const listed = await repo.list();
    if (!listed.ok) throw new Error("expected task list");
    expect(listed.value).toEqual(
      expect.arrayContaining([expect.objectContaining({ title: "Buy milk" })]),
    );
  });

  it("creates a task with the selected status and area", async () => {
    const response = await request("/tasks", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        title: "Plan",
        description: "",
        status: "done",
        area: "4",
      }).toString(),
    });
    expect(response.status).toBe(201);
    expect(response.headers.get("hx-redirect")).toBe("/tasks");
  });

  it("renders the new task page with cancel and form-owned side metadata", async () => {
    const body = await (await request("/tasks/new?area=3&status=done")).text();

    expect(body).toContain("New task");
    expect(body).toContain("Cancel");
    expect(body).toContain("Create");
    expect(body).toContain("status status--done");
    expect(body).toContain("status area-badge");
    expect(body).toContain('name="area" value="3" checked');
    expect(body).toContain("Apply area to this task");
  });
});

describe("Task creation origin tracking", () => {
  it("renders cancel returning to origin from the task list", async () => {
    const body = await (await request("/tasks/new?from=tasks&area=3&status=done")).text();

    expect(body).toContain('href="/tasks"');
    expect(body).toContain("New task");
    expect(body).toContain("Cancel");
  });

  it("renders cancel returning to the matrix from a matrix origin", async () => {
    const body = await (await request("/tasks/new?from=matrix&area=2&status=do")).text();

    expect(body).toContain('href="/"');
    expect(body).toContain("New task");
    expect(body).toContain("Cancel");
  });

  it("renders the matrix origin as a hidden form field", async () => {
    const body = await (await request("/tasks/new?from=matrix")).text();

    expect(body).toContain('name="from" value="matrix"');
  });

  it("renders cancel returning to the task list when origin is omitted", async () => {
    const body = await (await request("/tasks/new?area=1")).text();

    expect(body).toContain('href="/tasks"');
  });

  it("renders area creation links from the matrix with the matrix origin", async () => {
    await repo.insert(taskFixture({ id: "task-1", status: "do", area: 1 }));

    const body = await (await request("/")).text();

    expect(body).toContain('href="/tasks/new?area=1&amp;from=matrix"');
    expect(body).toContain('href="/tasks/new?area=2&amp;from=matrix"');
  });

  it("includes status and area choices in the create form", async () => {
    const body = await (await request("/tasks/new?from=tasks&area=3&status=do&menu=status")).text();

    expect(body).toContain('<form class="detail-grid"');
    expect(body).toContain('name="status" value="do" checked');
    expect(body).toContain('name="area" value="3" checked');
  });

  it("renders the task list New task link with the tasks origin", async () => {
    const body = await (await request("/tasks")).text();

    expect(body).toContain('href="/tasks/new?from=tasks"');
  });
});

describe("Task detail Save form", () => {
  it("renders a Save form when opened from the task list", async () => {
    await repo.insert(taskFixture({ id: "task-1", version: 3 }));

    const response = await request("/tasks/task-1?from=tasks");
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain('method="post"');
    expect(body).toContain('action="/tasks/task-1?from=tasks"');
    expect(body).toContain('hx-post="/tasks/task-1?from=tasks"');
    expect(body).toContain('id="task-version" type="hidden" name="version" value="3"');
    expect(body).toContain('<button class="button primary" type="submit">Save</button>');
    expect(body).toContain('href="/tasks"');
  });

  it("saves edits and redirects to the task list from the task-list detail form", async () => {
    await repo.insert(taskFixture({ id: "task-1", version: 3 }));

    const response = await request("/tasks/task-1?from=tasks", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        title: "updated task",
        description: "updated description",
        version: "3",
      }).toString(),
    });
    const saved = await repo.find("task-1", "local");

    expect(response.status).toBe(302);
    expect(response.headers.get("location")).toBe("/tasks");
    expect(saved).toEqual(
      expect.objectContaining({
        ok: true,
        value: expect.objectContaining({
          title: "updated task",
          description: "updated description",
          version: 4,
        }),
      }),
    );
  });

  it("returns an HTMX redirect to the matrix when saving matrix detail", async () => {
    await repo.insert(taskFixture({ id: "task-1", version: 3 }));

    const response = await request("/tasks/task-1?from=matrix", {
      method: "POST",
      headers: {
        "content-type": "application/x-www-form-urlencoded",
        "HX-Request": "true",
      },
      body: new URLSearchParams({
        title: "updated task",
        description: "updated description",
        version: "3",
      }).toString(),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("hx-redirect")).toBe("/");
  });
});

describe("Task detail and metadata menus", () => {
  it("renders detail and status/area menu fragments", async () => {
    await repo.insert(taskFixture({ id: "task-1", area: 1, status: "do" }));

    const detail = await request("/tasks/task-1");
    expect(detail.status).toBe(200);
    expect(await detail.text()).toContain("seed task");

    const matrixDetail = await request("/tasks/task-1?from=matrix");
    expect(await matrixDetail.text()).toContain('href="/"');

    const statusMenu = await request("/tasks/task-1/status/menu");
    const statusBody = await statusMenu.text();
    expect(statusMenu.status).toBe(200);
    expect(statusBody).toContain("do");
    expect(statusBody).toContain("done");
    expect(statusBody).toContain("skip");

    const areaMenu = await request("/tasks/task-1/area/menu");
    const areaBody = await areaMenu.text();
    expect(areaMenu.status).toBe(200);
    expect(areaBody).toContain("1");
    expect(areaBody).toContain("4");
  });

  it("renders popovers with selected and suggestion groups", async () => {
    await repo.insert(taskFixture({ id: "task-1", area: 1, status: "do" }));

    const statusBody = await (await request("/tasks/task-1/status/menu")).text();
    expect(statusBody).toContain("Apply status to this task");
    expect(statusBody).toContain("Selected status");
    expect(statusBody).toContain("Suggestions");
    expect(statusBody).toContain('hx-target="#task-meta"');

    const areaBody = await (await request("/tasks/task-1/area/menu")).text();
    expect(areaBody).toContain("Apply area to this task");
    expect(areaBody).toContain("Selected area");
  });

  it.each([
    ["status", "done", "/tasks/task-1/status"],
    ["area", "4", "/tasks/task-1/area"],
  ])("refreshes the form version after changing %s", async (_kind, value, path) => {
    await repo.insert(taskFixture({ id: "task-1", version: 3 }));

    const response = await request(path, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ [_kind]: value, version: "3" }).toString(),
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain('id="task-version" type="hidden" name="version" value="4" hx-swap-oob="true"');
  });
});
