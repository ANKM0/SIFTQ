import { describe, expect, it } from "vitest";
import app from "../src/index";

const HTMX_SCRIPT_URL =
  "https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js";
const HX_REQUEST = { "HX-Request": "true" };

async function requestBody(path: string, init?: RequestInit): Promise<string> {
  const response = await app.request(path, init);
  return response.text();
}

async function createTask(title: string): Promise<{ id: string; title: string }> {
  const response = await app.request("/tasks", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ title, description: "created by test" }).toString(),
  });

  expect([200, 201]).toContain(response.status);
  const id = (response.headers.get("hx-push-url") ?? "").split("/").at(-1) ?? "";
  expect(id).not.toBe("");
  return { id, title };
}

describe("GET / (Matrix)", () => {
  it("returns a full page with HTMX and no React client root", async () => {
    const response = await app.request("/");
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toMatch(/^text\/html/);
    expect(body).toContain("<html");
    expect(body).toContain('<main id="page">');
    expect(body).toContain(HTMX_SCRIPT_URL);
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
    const response = await app.request("/tasks");
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
    const response = await app.request("/tasks/new");
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
    const response = await app.request("/tasks", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ title, description: "hello" }).toString(),
    });
    const body = await response.text();

    expect([200, 201]).toContain(response.status);
    expect(response.headers.get("hx-push-url")).toMatch(/^\/tasks\//);
    expect(body).toContain(title);
    expect(body).toContain('<aside id="task-meta">');
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
    const response = await app.request(`/tasks/${id}`);
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
    const response = await app.request(`/tasks/${id}/status/menu`, {
      headers: HX_REQUEST,
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain(`hx-post="/tasks/${id}/status"`);
    expect(body).toContain("do");
    expect(body).toContain("done");
    expect(body).toContain("skip");
    expect(body).not.toContain("<html");
    expect(body).not.toContain("<script");
    expect(body).not.toContain('id="page"');
  });

  it("returns an area menu fragment with areas 1 to 4", async () => {
    const { id } = await createTask(`area menu ${Date.now()}`);
    const response = await app.request(`/tasks/${id}/area/menu`, {
      headers: HX_REQUEST,
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain(`hx-post="/tasks/${id}/area"`);
    expect(body).toContain("1");
    expect(body).toContain("2");
    expect(body).toContain("3");
    expect(body).toContain("4");
    expect(body).not.toContain("<html");
    expect(body).not.toContain("<script");
    expect(body).not.toContain('id="page"');
  });
});

describe("task edit", () => {
  it("updates title and description and returns a detail fragment", async () => {
    const { id } = await createTask(`edit target ${Date.now()}`);
    const newTitle = `edited title ${Date.now()}`;
    const response = await app.request(`/tasks/${id}`, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded", ...HX_REQUEST },
      body: new URLSearchParams({ title: newTitle, description: "updated" }).toString(),
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain(newTitle);
    expect(body).toContain('<aside id="task-meta">');
    expect(body).not.toContain("<html");
    expect(body).not.toContain("<script");
  });
});

describe("status change", () => {
  it("marks a task done and hides it from the Matrix but keeps it in the list", async () => {
    const { id, title } = await createTask(`status change ${Date.now()}`);
    const response = await app.request(`/tasks/${id}/status`, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded", ...HX_REQUEST },
      body: new URLSearchParams({ status: "done" }).toString(),
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
  });
});

describe("area change", () => {
  it("updates the area and returns a TaskMeta fragment", async () => {
    const { id } = await createTask(`area change ${Date.now()}`);
    const response = await app.request(`/tasks/${id}/area`, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded", ...HX_REQUEST },
      body: new URLSearchParams({ area: "4" }).toString(),
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain(`hx-get="/tasks/${id}/area/menu"`);
    expect(body).not.toContain("<html");
    expect(body).not.toContain("<script");
  });
});

describe("validation", () => {
  it("rejects an empty title with a 200 inline error form fragment", async () => {
    const response = await app.request("/tasks", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded", ...HX_REQUEST },
      body: new URLSearchParams({ title: "", description: "" }).toString(),
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(response.headers.get("hx-push-url")).toBeNull();
    expect(body).toContain('hx-post="/tasks"');
    expect(body).not.toContain('<aside id="task-meta">');
  });

  it("rejects a title over 256 characters with a 200 inline error form fragment", async () => {
    const response = await app.request("/tasks", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded", ...HX_REQUEST },
      body: new URLSearchParams({ title: "a".repeat(257), description: "" }).toString(),
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(response.headers.get("hx-push-url")).toBeNull();
    expect(body).toContain('hx-post="/tasks"');
    expect(body).not.toContain('<aside id="task-meta">');
  });
});
