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
    expect(body).toContain('href="/tasks/new?area=1"');
    expect(body).toContain('href="/tasks/task-1?from=matrix"');
    expect(body).toContain("status--do");
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
  it("creates a task and returns the detail page", async () => {
    const response = await request("/tasks", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ title: "Buy milk", description: "low-fat" }).toString(),
    });
    const body = await response.text();

    expect([200, 201]).toContain(response.status);
    expect(response.headers.get("hx-push-url")).toMatch(/^\/tasks\//);
    expect(body).toContain("Buy milk");
    expect(body).toContain('id="task-meta"');
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
    const body = await response.text();

    expect(response.status).toBe(201);
    expect(body).toContain("status--done");
    expect(body).toContain(">4</a>");
  });

  it("renders the new task page with cancel and side metadata", async () => {
    const body = await (await request("/tasks/new?area=3&status=done&menu=area")).text();

    expect(body).toContain("New task");
    expect(body).toContain("Cancel");
    expect(body).toContain("Create");
    expect(body).toContain("status status--done");
    expect(body).toContain("status area-badge");
    expect(body).toContain('name="area" value="3"');
    expect(body).toContain("Apply area to this task");
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
});
