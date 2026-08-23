import { beforeEach, describe, expect, it } from "vitest";
import app from "../src/index";
import type { Task } from "../src/task";
import type { TaskRepository } from "../src/task-repository";

const HTMX_SCRIPT_URL =
  "https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js";
const SORTABLE_SCRIPT_URL =
  "https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js";
const HX_REQUEST = { "HX-Request": "true" };

function task(
  id: string,
  title: string,
  status: Task["status"],
  area: Task["area"],
  order: number,
): Task {
  return { id, title, description: "", status, area, order, version: 1 };
}

function seedTasks(): Task[] {
  return [
    task("seed-1", "Set up D1 database", "do", 1, 0),
    task("seed-2", "Adopt version optimistic locking", "do", 1, 1),
    task("seed-3", "Move Matrix to HTMX partial updates", "do", 2, 0),
    task("seed-4", "Add SortableJS drag and drop", "do", 3, 0),
    task("seed-5", "Review ADR 0007", "done", 4, 0),
  ];
}

class MemoryTaskRepository implements TaskRepository {
  private tasks: Task[];

  constructor(tasks: readonly Task[]) {
    this.tasks = tasks.map((item) => ({ ...item }));
  }

  async list(): Promise<Task[]> {
    return this.tasks.map((item) => ({ ...item }));
  }

  async find(id: string): Promise<Task | undefined> {
    const found = this.tasks.find((item) => item.id === id);
    return found === undefined ? undefined : { ...found };
  }

  async insert(item: Task): Promise<Task> {
    this.tasks.push({ ...item });
    return { ...item };
  }

  async update(item: Task): Promise<Task | "conflict"> {
    const index = this.tasks.findIndex((candidate) => candidate.id === item.id);
    const current = this.tasks[index];
    if (!current || current.version !== item.version) return "conflict";
    const updated = { ...item, version: item.version + 1 };
    this.tasks[index] = updated;
    return updated;
  }

  async move(items: readonly Task[]): Promise<Task[] | "conflict"> {
    const byId = new Map(this.tasks.map((item) => [item.id, item]));
    for (const item of items) {
      const current = byId.get(item.id);
      if (!current || current.version !== item.version) return "conflict";
    }

    const updated = items.map((item) => ({
      ...item,
      version: item.version + 1,
    }));
    for (const item of updated) {
      const index = this.tasks.findIndex(
        (candidate) => candidate.id === item.id,
      );
      if (index < 0) return "conflict";
      this.tasks[index] = item;
    }
    return updated;
  }
}

let repo: MemoryTaskRepository;

beforeEach(() => {
  repo = new MemoryTaskRepository(seedTasks());
});

async function request(path: string, init?: RequestInit): Promise<Response> {
  return await app.request(path, init, { TASK_REPOSITORY: repo });
}

async function requestBody(path: string, init?: RequestInit): Promise<string> {
  const response = await request(path, init);
  return response.text();
}

async function createTask(
  title: string,
): Promise<{ id: string; title: string; version: number }> {
  const response = await request("/tasks", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ title, description: "created by test" }).toString(),
  });

  expect([200, 201]).toContain(response.status);
  const id = (response.headers.get("hx-push-url") ?? "").split("/").at(-1) ?? "";
  expect(id).not.toBe("");
  return { id, title, version: 1 };
}

function matrixAreaTaskIds(body: string, area: number): string[] {
  const section = body.match(
    new RegExp(
      `<section class="matrix-area" data-area="${area}">([\\s\\S]*?)</section>`,
    ),
  );
  const ids = [...(section?.[1]?.matchAll(/data-task-id="([^"]+)"/g) ?? [])];
  return ids
    .map((match) => match[1])
    .filter((id): id is string => id !== undefined);
}

describe("GET / (Matrix)", () => {
  it("returns a full page with HTMX and no React client root", async () => {
    const response = await request("/");
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toMatch(/^text\/html/);
    expect(body).toContain("<html");
    expect(body).toContain('<main id="page">');
    expect(body).toContain(HTMX_SCRIPT_URL);
    expect(body).toContain(SORTABLE_SCRIPT_URL);
    expect(body).toContain("Sortable.create(list");
    expect(body).toContain('addEventListener("htmx:load", initMatrixSortable)');
    expect(body).toContain('setAttribute("data-version", nextVersion)');
    expect(body).toContain('data-sortable-group="matrix"');
    expect(body).toContain('data-task-id="seed-1"');
    expect(body).toContain('data-version="1"');
    expect(body).toContain('data-area="1"');
    expect(body).toContain('hx-get="/tasks/new"');
    expect(body).toContain('hx-target="#page"');
    expect(body).toContain('hx-swap="innerHTML"');
    expect(body).toContain('hx-push-url="true"');
    expect(body).not.toMatch(/\bid=["']root["']/i);
    expect(body).not.toContain("createRoot");
  });

  it("returns a page fragment for an HX-Request without layout", async () => {
    const body = await requestBody("/", { headers: HX_REQUEST });

    expect(body).toContain('hx-get="/tasks/new"');
    expect(body).not.toContain("<html");
    expect(body).not.toContain("<head");
    expect(body).not.toContain("<script");
    expect(body).not.toContain('id="page"');
  });
});

describe("GET /tasks (list)", () => {
  it("returns a full list page with HTMX", async () => {
    const response = await request("/tasks");
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain("<html");
    expect(body).toContain('<main id="page">');
    expect(body).toContain(HTMX_SCRIPT_URL);
  });

  it("returns a list fragment for an HX-Request without layout", async () => {
    const body = await requestBody("/tasks", { headers: HX_REQUEST });

    expect(body).not.toContain("<html");
    expect(body).not.toContain("<head");
    expect(body).not.toContain("<script");
    expect(body).not.toContain('id="page"');
  });
});

describe("GET /tasks/new", () => {
  it("returns a full page with a constrained title input and hx-post form", async () => {
    const response = await request("/tasks/new");
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain("<html");
    expect(body).toContain('<main id="page">');
    expect(body).toContain(HTMX_SCRIPT_URL);
    expect(body).toContain('hx-post="/tasks"');
    expect(body).toContain('hx-target="#page"');
    expect(body).toContain('hx-swap="innerHTML"');
    expect(body).toContain('name="title"');
    expect(body).toContain('name="description"');
    expect(body).toContain('maxlength="256"');
    expect(body).toContain('required=""');
  });
});

describe("task creation", () => {
  it("creates a task and pushes the detail URL", async () => {
    const title = `created task ${Date.now()}`;
    const response = await request("/tasks", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ title, description: "hello" }).toString(),
    });
    const body = await response.text();

    expect([200, 201]).toContain(response.status);
    expect(response.headers.get("hx-push-url")).toMatch(/^\/tasks\//);
    expect(body).toContain(title);
    expect(body).toContain('<aside id="task-meta">');
    expect(body).toContain('name="version" value="1"');
    expect(body).not.toContain("<html");
    expect(body).not.toContain("<script");
  });

  it("shows a created task in the list and the Matrix", async () => {
    const { title } = await createTask(`visible task ${Date.now()}`);

    const listBody = await requestBody("/tasks", { headers: HX_REQUEST });
    expect(listBody).toContain(title);

    const matrixBody = await requestBody("/", { headers: HX_REQUEST });
    expect(matrixBody).toContain(title);
  });
});

describe("task detail", () => {
  it("returns a full detail page with edit form and metadata menus", async () => {
    const { id, title } = await createTask(`detail task ${Date.now()}`);
    const response = await request(`/tasks/${id}`);
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain("<html");
    expect(body).toContain('<main id="page">');
    expect(body).toContain(HTMX_SCRIPT_URL);
    expect(body).toContain(title);
    expect(body).toContain(`hx-post="/tasks/${id}"`);
    expect(body).toContain('<aside id="task-meta">');
    expect(body).toContain(`hx-get="/tasks/${id}/status/menu"`);
    expect(body).toContain(`hx-get="/tasks/${id}/area/menu"`);
    expect(body).toContain('name="version" value="1"');
  });

  it("returns a detail fragment for an HX-Request without layout", async () => {
    const { id } = await createTask(`detail fragment ${Date.now()}`);
    const body = await requestBody(`/tasks/${id}`, { headers: HX_REQUEST });

    expect(body).toContain(`hx-post="/tasks/${id}"`);
    expect(body).toContain('<aside id="task-meta">');
    expect(body).not.toContain("<html");
    expect(body).not.toContain("<head");
    expect(body).not.toContain("<script");
    expect(body).not.toContain('id="page"');
  });
});

describe("metadata menus", () => {
  it("returns a status menu fragment with do, done and skip", async () => {
    const { id } = await createTask(`status menu ${Date.now()}`);
    const response = await request(`/tasks/${id}/status/menu`, {
      headers: HX_REQUEST,
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain(`hx-post="/tasks/${id}/status"`);
    expect(body).toContain("do");
    expect(body).toContain("done");
    expect(body).toContain("skip");
    expect(body).toContain("&quot;version&quot;:1");
    expect(body).not.toContain("<html");
    expect(body).not.toContain("<script");
    expect(body).not.toContain('id="page"');
  });

  it("returns an area menu fragment with areas 1 to 4", async () => {
    const { id } = await createTask(`area menu ${Date.now()}`);
    const response = await request(`/tasks/${id}/area/menu`, {
      headers: HX_REQUEST,
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain(`hx-post="/tasks/${id}/area"`);
    expect(body).toContain("1");
    expect(body).toContain("2");
    expect(body).toContain("3");
    expect(body).toContain("4");
    expect(body).toContain("&quot;version&quot;:1");
    expect(body).not.toContain("<html");
    expect(body).not.toContain("<script");
    expect(body).not.toContain('id="page"');
  });
});

describe("task edit", () => {
  it("updates title and description and returns a detail fragment", async () => {
    const { id } = await createTask(`edit target ${Date.now()}`);
    const newTitle = `edited title ${Date.now()}`;
    const response = await request(`/tasks/${id}`, {
      method: "POST",
      headers: {
        "content-type": "application/x-www-form-urlencoded",
        ...HX_REQUEST,
      },
      body: new URLSearchParams({
        title: newTitle,
        description: "updated",
        version: "1",
      }).toString(),
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain(newTitle);
    expect(body).toContain('<aside id="task-meta">');
    expect(body).toContain('name="version" value="2"');
    expect(body).not.toContain("<html");
    expect(body).not.toContain("<script");
  });
});

describe("status change", () => {
  it("marks a task done and hides it from the Matrix but keeps it in the list", async () => {
    const { id, title } = await createTask(`status change ${Date.now()}`);
    const response = await request(`/tasks/${id}/status`, {
      method: "POST",
      headers: {
        "content-type": "application/x-www-form-urlencoded",
        ...HX_REQUEST,
      },
      body: new URLSearchParams({ status: "done", version: "1" }).toString(),
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain(`hx-get="/tasks/${id}/status/menu"`);
    expect(body).not.toContain("<html");
    expect(body).not.toContain("<script");

    const matrixBody = await requestBody("/", { headers: HX_REQUEST });
    expect(matrixBody).not.toContain(title);

    const listBody = await requestBody("/tasks", { headers: HX_REQUEST });
    expect(listBody).toContain(title);

    const detailBody = await requestBody(`/tasks/${id}`, { headers: HX_REQUEST });
    expect(detailBody).toContain('name="version" value="2"');
  });
});

describe("area change", () => {
  it("updates the area and returns a TaskMeta fragment", async () => {
    const { id } = await createTask(`area change ${Date.now()}`);
    const response = await request(`/tasks/${id}/area`, {
      method: "POST",
      headers: {
        "content-type": "application/x-www-form-urlencoded",
        ...HX_REQUEST,
      },
      body: new URLSearchParams({ area: "4", version: "1" }).toString(),
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain(`hx-get="/tasks/${id}/area/menu"`);
    expect(body).not.toContain("<html");
    expect(body).not.toContain("<script");

    const detailBody = await requestBody(`/tasks/${id}`, { headers: HX_REQUEST });
    expect(detailBody).toContain('name="version" value="2"');
  });
});

describe("matrix move across areas", () => {
  it("moves a task to another area through the move endpoint", async () => {
    const { id } = await createTask(`move area ${Date.now()}`);
    const response = await request(`/tasks/${id}/move`, {
      method: "POST",
      headers: {
        "content-type": "application/x-www-form-urlencoded",
        ...HX_REQUEST,
      },
      body: new URLSearchParams({
        area: "4",
        order: "0",
        version: "1",
      }).toString(),
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain('data-sortable-group="matrix"');
    expect(body).not.toContain("<html");
    expect(body).not.toContain("<script");
    expect(matrixAreaTaskIds(body, 4)).toContain(id);
    expect(matrixAreaTaskIds(body, 1)).not.toContain(id);

    const matrixBody = await requestBody("/", { headers: HX_REQUEST });
    expect(matrixAreaTaskIds(matrixBody, 4)).toContain(id);
    expect(matrixAreaTaskIds(matrixBody, 1)).not.toContain(id);
  });

  it("returns the incremented version for the moved task", async () => {
    const { id } = await createTask(`move version ${Date.now()}`);
    const response = await request(`/tasks/${id}/move`, {
      method: "POST",
      headers: {
        "content-type": "application/x-www-form-urlencoded",
        ...HX_REQUEST,
      },
      body: new URLSearchParams({
        area: "4",
        order: "0",
        version: "1",
      }).toString(),
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain(`data-task-id="${id}" data-version="2"`);
  });
});

describe("matrix move inside an area", () => {
  it("reorders tasks inside the same area through the move endpoint", async () => {
    const first = await createTask(`move first ${Date.now()}`);
    const second = await createTask(`move second ${Date.now()}`);
    const before = await requestBody("/", { headers: HX_REQUEST });
    const beforeIds = matrixAreaTaskIds(before, 1);
    const firstIndex = beforeIds.indexOf(first.id);
    const secondIndex = beforeIds.indexOf(second.id);

    expect(firstIndex).toBeGreaterThanOrEqual(0);
    expect(secondIndex).toBeGreaterThan(firstIndex);

    const response = await request(`/tasks/${first.id}/move`, {
      method: "POST",
      headers: {
        "content-type": "application/x-www-form-urlencoded",
        ...HX_REQUEST,
      },
      body: new URLSearchParams({
        area: "1",
        order: String(secondIndex),
        version: "1",
      }).toString(),
    });
    const body = await response.text();
    const afterIds = matrixAreaTaskIds(body, 1);

    expect(response.status).toBe(200);
    expect(afterIds.indexOf(first.id)).toBeGreaterThan(
      afterIds.indexOf(second.id),
    );
  });
});

describe("matrix move validation", () => {
  it("rejects invalid move input and leaves the task in its area", async () => {
    const { id } = await createTask(`invalid move ${Date.now()}`);
    const response = await request(`/tasks/${id}/move`, {
      method: "POST",
      headers: {
        "content-type": "application/x-www-form-urlencoded",
        ...HX_REQUEST,
      },
      body: new URLSearchParams({
        area: "9",
        order: "0",
        version: "1",
      }).toString(),
    });

    expect(response.status).toBe(400);

    const matrixBody = await requestBody("/", { headers: HX_REQUEST });
    expect(matrixAreaTaskIds(matrixBody, 1)).toContain(id);
  });

  it("rejects an invalid order and leaves the task in its area", async () => {
    const { id } = await createTask(`invalid order ${Date.now()}`);
    const response = await request(`/tasks/${id}/move`, {
      method: "POST",
      headers: {
        "content-type": "application/x-www-form-urlencoded",
        ...HX_REQUEST,
      },
      body: new URLSearchParams({
        area: "1",
        order: "abc",
        version: "1",
      }).toString(),
    });

    expect(response.status).toBe(400);

    const matrixBody = await requestBody("/", { headers: HX_REQUEST });
    expect(matrixAreaTaskIds(matrixBody, 1)).toContain(id);
  });

  it("returns 404 when the task does not exist", async () => {
    const response = await request("/tasks/missing-task/move", {
      method: "POST",
      headers: {
        "content-type": "application/x-www-form-urlencoded",
        ...HX_REQUEST,
      },
      body: new URLSearchParams({
        area: "1",
        order: "0",
        version: "1",
      }).toString(),
    });

    expect(response.status).toBe(404);
  });
});

describe("validation", () => {
  it("rejects an empty title with a 200 inline error form fragment", async () => {
    const response = await request("/tasks", {
      method: "POST",
      headers: {
        "content-type": "application/x-www-form-urlencoded",
        ...HX_REQUEST,
      },
      body: new URLSearchParams({ title: "", description: "" }).toString(),
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(response.headers.get("hx-push-url")).toBeNull();
    expect(body).toContain('hx-post="/tasks"');
    expect(body).not.toContain('<aside id="task-meta">');
  });

  it("rejects a title over 256 characters with a 200 inline error form fragment", async () => {
    const response = await request("/tasks", {
      method: "POST",
      headers: {
        "content-type": "application/x-www-form-urlencoded",
        ...HX_REQUEST,
      },
      body: new URLSearchParams({
        title: "a".repeat(257),
        description: "",
      }).toString(),
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(response.headers.get("hx-push-url")).toBeNull();
    expect(body).toContain('hx-post="/tasks"');
    expect(body).not.toContain('<aside id="task-meta">');
  });
});

describe("optimistic version locking", () => {
  it("returns 409 when an edit uses a stale version", async () => {
    const { id } = await createTask(`conflict edit ${Date.now()}`);

    const first = await request(`/tasks/${id}`, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        title: "first update",
        description: "",
        version: "1",
      }).toString(),
    });
    expect(first.status).toBe(200);

    const second = await request(`/tasks/${id}`, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        title: "second update",
        description: "",
        version: "1",
      }).toString(),
    });
    const body = await second.text();

    expect(second.status).toBe(409);
    expect(body).toContain("Task was updated elsewhere.");
    expect(body).toContain(`hx-get="/tasks/${id}"`);
  });

  it("returns 409 when a status change uses a stale version", async () => {
    const { id } = await createTask(`conflict status ${Date.now()}`);

    await request(`/tasks/${id}/status`, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ status: "done", version: "1" }).toString(),
    });

    const second = await request(`/tasks/${id}/status`, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ status: "do", version: "1" }).toString(),
    });

    expect(second.status).toBe(409);
  });
});

describe("matrix move conflict", () => {
  it("returns 409 when a move uses a stale version", async () => {
    const { id } = await createTask(`conflict move ${Date.now()}`);

    await request(`/tasks/${id}/status`, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ status: "done", version: "1" }).toString(),
    });

    const response = await request(`/tasks/${id}/move`, {
      method: "POST",
      headers: {
        "content-type": "application/x-www-form-urlencoded",
        ...HX_REQUEST,
      },
      body: new URLSearchParams({
        area: "2",
        order: "0",
        version: "1",
      }).toString(),
    });

    expect(response.status).toBe(409);
  });
});
