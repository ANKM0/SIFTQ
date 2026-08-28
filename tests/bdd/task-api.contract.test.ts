import { beforeEach, describe, expect, it } from "vite-plus/test";
import type { Task } from "../../src/task";
import { authenticatedRequest } from "../helpers/authenticated-request";
import { taskFixture } from "../helpers/task-fixture";
import { MemoryTaskRepository } from "../helpers/memory-task-repository";

let repo: MemoryTaskRepository;

beforeEach(() => {
  repo = new MemoryTaskRepository();
});

function request(method: string, path: string, body?: unknown) {
  const init: RequestInit = {
    method,
    headers: { "content-type": "application/json" },
  };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
  }

  return authenticatedRequest(path, repo, init);
}

describe("BDD-TM-001: task creation", () => {
  it("returns 201 and the created task attributes", async () => {
    const response = await request("POST", "/api/tasks", {
      title: "Buy milk",
      description: "low-fat",
    });

    expect(response.status).toBe(201);
    expect(response.headers.get("location")).toMatch(/^\/api\/tasks\//);

    const task: Task = await response.json();
    expect(task.title).toBe("Buy milk");
    expect(task.description).toBe("low-fat");
    expect(task.status).toBe("do");
    expect(task.area).toBe(1);
    expect(task.order).toBe(1);
    expect(task.version).toBe(1);
    expect(task.id).toEqual(expect.any(String));
  });
});

describe("BDD-TM-002 / BDD-TM-003: task list", () => {
  it("returns active tasks in the list", async () => {
    await repo.insert(taskFixture({ id: "task-1", status: "do" }));

    const response = await request("GET", "/api/tasks");
    const tasks: Task[] = await response.json();

    expect(response.status).toBe(200);
    expect(tasks.map((task) => task.id)).toContain("task-1");
  });

  it("keeps done and skip tasks in the list", async () => {
    await repo.insert(taskFixture({ id: "done-1", status: "done" }));
    await repo.insert(taskFixture({ id: "skip-1", status: "skip" }));

    const response = await request("GET", "/api/tasks");
    const tasks: Task[] = await response.json();

    expect(response.status).toBe(200);
    expect(tasks.map((task) => task.id)).toEqual(expect.arrayContaining(["done-1", "skip-1"]));
  });
});

describe("BDD-TM-005 / BDD-TM-006: task update", () => {
  it("updates title and description", async () => {
    await repo.insert(taskFixture({ id: "task-1" }));

    const response = await request("PATCH", "/api/tasks/task-1", {
      title: "new title",
      description: "new description",
      version: 1,
    });
    const task: Task = await response.json();

    expect(response.status).toBe(200);
    expect(task.title).toBe("new title");
    expect(task.description).toBe("new description");
  });

  it("updates status and area", async () => {
    await repo.insert(taskFixture({ id: "task-1" }));

    const response = await request("PATCH", "/api/tasks/task-1", {
      status: "done",
      area: 4,
      version: 1,
    });
    const task: Task = await response.json();

    expect(response.status).toBe(200);
    expect(task.status).toBe("done");
    expect(task.area).toBe(4);
  });
});

describe("BDD-TM-008: bulk reorder", () => {
  it("moves a task to another area and order", async () => {
    await repo.insert(taskFixture({ id: "task-1" }));

    const response = await request("POST", "/api/tasks/reorder", {
      id: "task-1",
      area: 2,
      order: 0,
      version: 1,
    });
    const task: Task = await response.json();

    expect(response.status).toBe(200);
    expect(task.area).toBe(2);
    expect(task.order).toBe(0);
  });
});

describe("BDD-TM-009: reorder conflict", () => {
  it("returns 409 with code CONFLICT for a stale version", async () => {
    await repo.insert(taskFixture({ id: "task-1", version: 2 }));

    const response = await request("POST", "/api/tasks/reorder", {
      id: "task-1",
      area: 2,
      order: 0,
      version: 1,
    });
    const body: { code?: string } = await response.json();

    expect(response.status).toBe(409);
    expect(response.headers.get("content-type")).toMatch(/^application\/json/);
    expect(body.code).toBe("CONFLICT");
  });
});
