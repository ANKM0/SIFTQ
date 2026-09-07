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

async function seedDoTasks(count: number) {
  for (let index = 1; index <= count; index += 1) {
    const id = `seed-${String(index).padStart(3, "0")}`;
    await repo.insert(taskFixture({ id, title: `seed title ${index}`, status: "do" }));
  }
}

function countTaskRows(body: string): number {
  return body.split('class="task-row"').length - 1;
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
    expect(body).not.toContain("status--do");
  });
});

describe("Task list page", () => {
  it("defaults to do and renders status filter controls", async () => {
    await repo.insert(taskFixture({ id: "do-1", status: "do" }));
    await repo.insert(taskFixture({ id: "done-1", status: "done" }));
    await repo.insert(taskFixture({ id: "skip-1", status: "skip" }));

    const response = await request("/tasks");
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain("do-1");
    expect(body).not.toContain("done-1");
    expect(body).not.toContain("skip-1");
    expect(body).toContain('aria-label="Filter tasks by status"');
    expect(body).toContain('aria-current="true" href="/tasks?status=do"');
    expect(body).toContain('href="/tasks?status=done"');
    expect(body).toContain('href="/tasks?status=skip"');
  });

  it.each(["do", "done", "skip"] as const)("filters tasks by %s status", async (status) => {
    await repo.insert(taskFixture({ id: "do-1", status: "do" }));
    await repo.insert(taskFixture({ id: "done-1", status: "done" }));
    await repo.insert(taskFixture({ id: "skip-1", status: "skip" }));

    const body = await (await request(`/tasks?status=${status}`)).text();

    for (const candidate of ["do", "done", "skip"] as const) {
      const id = `${candidate}-1`;
      if (candidate === status) {
        expect(body).toContain(id);
      } else {
        expect(body).not.toContain(id);
      }
    }
    expect(body).toContain(`aria-current="true" href="/tasks?status=${status}"`);
  });

  it("falls back to do for an unknown status and displays an empty-state message", async () => {
    await repo.insert(taskFixture({ id: "done-1", status: "done" }));

    const fallbackBody = await (await request("/tasks?status=unknown")).text();
    expect(fallbackBody).toContain('aria-current="true" href="/tasks?status=do"');
    expect(fallbackBody).not.toContain("done-1");

    const emptyBody = await (await request("/tasks?status=skip")).text();
    expect(emptyBody).toContain("該当するtaskはありません。");
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

describe("Task list working filter", () => {
  it("filters the list to working tasks only when requested", async () => {
    await repo.insert(
      taskFixture({ id: "working-1", status: "do", working: true, title: "working task" }),
    );
    await repo.insert(taskFixture({ id: "idle-1", status: "do", working: false, title: "idle task" }));
    await repo.insert(
      taskFixture({
        id: "working-done-1",
        status: "done",
        working: true,
        title: "done working task",
      }),
    );

    const body = await (await request("/tasks?status=do&working=only")).text();

    expect(body).toContain("working task");
    expect(body).not.toContain("idle task");
    expect(body).not.toContain("done working task");
    expect(body).toContain("working only");
  });

  it("keeps the status filter when toggling the working filter", async () => {
    const body = await (await request("/tasks?status=done")).text();

    expect(body).toContain('href="/tasks?status=done&amp;working=only"');
  });

  it("preserves the status filter on working filter links", async () => {
    const body = await (await request("/tasks?status=skip")).text();

    expect(body).toContain('href="/tasks?status=skip&amp;working=only"');
  });
});

describe("Task list pagination", () => {
  it("hides the page nav for 25 or fewer tasks", async () => {
    await seedDoTasks(25);

    const body = await (await request("/tasks?status=do")).text();

    expect(countTaskRows(body)).toBe(25);
    expect(body).not.toContain('aria-label="Task list pages"');
  });

  it("shows the first 25 tasks on page 1", async () => {
    await seedDoTasks(26);

    const firstBody = await (await request("/tasks?status=do")).text();
    expect(countTaskRows(firstBody)).toBe(25);
    expect(firstBody).toContain("seed-001");
    expect(firstBody).toContain("seed-025");
    expect(firstBody).not.toContain("seed-026");
    expect(firstBody).toContain("#25");
    expect(firstBody).toContain('href="/tasks?status=do&amp;page=2"');
    expect(firstBody).toContain('aria-current="page"');
    expect(firstBody).toContain('aria-disabled="true"');
    expect(firstBody).toContain("前へ");
    expect(firstBody).toContain("次へ");
  });

  it("shows the remaining tasks on page 2 with continuing issue numbers", async () => {
    await seedDoTasks(26);

    const secondBody = await (await request("/tasks?status=do&page=2")).text();
    expect(countTaskRows(secondBody)).toBe(1);
    expect(secondBody).toContain("seed-026");
    expect(secondBody).not.toContain("seed-001");
    expect(secondBody).toContain("#26");
    expect(secondBody).toContain('href="/tasks?status=do&amp;page=1"');
  });

  it("keeps status filter links on page 1", async () => {
    await seedDoTasks(26);

    const body = await (await request("/tasks?status=do&page=2")).text();

    expect(body).toContain('href="/tasks?status=done"');
    expect(body).not.toContain("status=done&amp;page");
  });

  it("falls back to page 1 for a non-numeric page and clamps overflow to the last page", async () => {
    await seedDoTasks(26);

    const invalidBody = await (await request("/tasks?status=do&page=abc")).text();
    expect(countTaskRows(invalidBody)).toBe(25);
    expect(invalidBody).toContain("seed-001");

    const overflowBody = await (await request("/tasks?status=do&page=999")).text();
    expect(countTaskRows(overflowBody)).toBe(1);
    expect(overflowBody).toContain("seed-026");
  });

  it("collapses the gap between the ends and the middle pages", async () => {
    await seedDoTasks(250);

    const body = await (await request("/tasks?status=do&page=5")).text();

    expect(body.split("pagination-ellipsis").length - 1).toBe(2);
    expect(body).toContain('href="/tasks?status=do&amp;page=1"');
    expect(body).toContain('href="/tasks?status=do&amp;page=10"');
    expect(body).toContain('aria-current="page"');
  });

  it("hides the page nav for an empty filtered list", async () => {
    const body = await (await request("/tasks?status=skip")).text();

    expect(body).toContain("該当するtaskはありません。");
    expect(body).not.toContain('aria-label="Task list pages"');
  });
});

describe("Task list working and pagination interaction", () => {
  it("keeps the working filter in pagination links", async () => {
    await repo.insert(
      taskFixture({ id: "working-1", status: "do", working: true, title: "working task" }),
    );

    const body = await (await request("/tasks?status=do&working=only")).text();

    expect(body).toContain("working task");
  });

  it("resets to page 1 when switching status from a working-filtered page", async () => {
    const body = await (await request("/tasks?status=do&working=only&page=2")).text();

    expect(body).toContain('href="/tasks?status=done&amp;working=only"');
    expect(body).not.toContain("status=done&amp;working=only&amp;page");
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
    expect(body).toContain('data-task-form="new"');
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
    expect(body).toContain('data-task-form="edit"');
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

describe("Task detail working toggle", () => {
  it("toggles working from the detail metadata and refreshes the version", async () => {
    await repo.insert(taskFixture({ id: "task-1", version: 3, working: false }));

    const response = await request("/tasks/task-1/working", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ working: "true", version: "3" }).toString(),
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain(
      'id="task-version" type="hidden" name="version" value="4" hx-swap-oob="true"',
    );
    expect(body).toContain(">working</button>");

    const saved = await repo.find("task-1", "local");
    expect(saved).toEqual(expect.objectContaining({ ok: true }));
    if (saved.ok && saved.value) expect(saved.value.working).toBe(true);
  });

  it("rejects an invalid working value from the detail metadata", async () => {
    await repo.insert(taskFixture({ id: "task-1", version: 3 }));

    const response = await request("/tasks/task-1/working", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ working: "yes", version: "3" }).toString(),
    });

    expect(response.status).toBe(400);
  });
});
