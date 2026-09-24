import { describe, expect, it } from "vite-plus/test";
import app from "../src/index";
import { createSession, SESSION_COOKIE_NAME } from "../src/auth";
import { createMemoryIdeaRepository } from "../src/preview/MemoryIdeaRepository";
import { createMemoryTaskRepository } from "../src/preview/MemoryTaskRepository";

const SECRET = "idea-api-test-secret";
const PASSWORD = atob("dGVzdC1wYXNzd29yZA==");
const taskRepository = createMemoryTaskRepository();
const ideaRepository = createMemoryIdeaRepository();

async function request(path: string, init: RequestInit = {}) {
  const cookie = await createSession(SECRET, Date.now() + 60_000);
  const headers = new Headers(init.headers);
  headers.set("Cookie", `${SESSION_COOKIE_NAME}=${cookie}`);
  return app.request(path, { ...init, headers }, {
    AUTH_PASSWORD: PASSWORD,
    SESSION_SECRET: SECRET,
    TASK_REPOSITORY: taskRepository,
    IDEA_REPOSITORY: ideaRepository,
  });
}

describe("Idea API", () => {
  it("persists create, edit, pin, reorder, and delete through the repository", async () => {
    const first = await request("/api/ideas", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: "first", description: "memo" }),
    });
    const second = await request("/api/ideas", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: "second", description: "" }),
    });
    expect(first.status).toBe(201);
    expect(second.status).toBe(201);

    const firstIdea = await first.json();
    const secondIdea = await second.json();
    const edited = await request(`/api/ideas/${firstIdea.id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: "edited", description: "updated", pinned: true, order: 1 }),
    });
    expect(edited.status).toBe(200);

    const reordered = await request("/api/ideas/reorder", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ ideas: [{ id: secondIdea.id, order: 1 }, { id: firstIdea.id, order: 2 }] }),
    });
    expect(reordered.status).toBe(200);

    const listed = await request("/api/ideas");
    expect(await listed.json()).toEqual([
      expect.objectContaining({ id: firstIdea.id, title: "edited", pinned: true, order: 2 }),
      expect.objectContaining({ id: secondIdea.id, order: 1 }),
    ]);

    const removed = await request(`/api/ideas/${firstIdea.id}`, { method: "DELETE" });
    expect(removed.status).toBe(204);
  });

  it("rejects an invalid title at the API boundary", async () => {
    const response = await request("/api/ideas", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: "", description: "" }),
    });
    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ code: "INVALID_TITLE" });
  });
});
