import { beforeEach, describe, expect, it } from "vite-plus/test";
import app from "../../src/index";
import { taskFixture } from "../helpers/task-fixture";
import { MemoryTaskRepository } from "../helpers/memory-task-repository";

let repo: MemoryTaskRepository;

beforeEach(() => {
  repo = new MemoryTaskRepository();
});

function request(path: string, init?: RequestInit) {
  return app.request(path, init, { TASK_REPOSITORY: repo });
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
    expect(body).toContain('<aside id="task-meta">');
  });
});

describe("Task detail and metadata menus", () => {
  it("renders detail and status/area menu fragments", async () => {
    await repo.insert(taskFixture({ id: "task-1", area: 1, status: "do" }));

    const detail = await request("/tasks/task-1");
    expect(detail.status).toBe(200);
    expect(await detail.text()).toContain("seed task");

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
});
