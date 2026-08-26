import { Hono } from "hono";
import type { Context } from "hono";
import type { ContentfulStatusCode } from "hono/utils/http-status";
import type { D1Database } from "@cloudflare/workers-types";
import {
  changeTaskArea,
  changeTaskStatus,
  createTask,
  isTaskArea,
  isTaskStatus,
  isTaskTitleValid,
  moveTask,
} from "./task";
import type { Task } from "./task";
import { D1TaskRepository } from "./task-repository";
import type { TaskRepository } from "./task-repository";

type Env = {
  TASK_REPOSITORY?: TaskRepository;
  DB?: D1Database;
};

type AppEnv = {
  Bindings: Env;
};

const app = new Hono<AppEnv>();

function repository(c: Context<AppEnv>): TaskRepository {
  if (c.env.TASK_REPOSITORY) return c.env.TASK_REPOSITORY;
  if (c.env.DB) return new D1TaskRepository(c.env.DB);
  throw new Error("task repository is not configured");
}

function problem(c: Context<AppEnv>, status: ContentfulStatusCode, code: string) {
  return c.json({ code }, status);
}

function parseVersion(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1) {
    return null;
  }
  return value;
}

function applyPatch(
  body: Record<string, unknown>,
  task: Task,
): { ok: true; task: Task } | { ok: false; code: string } {
  const withTitle = applyTitle(body, task);
  if (!withTitle) return { ok: false, code: "INVALID_TITLE" };

  const withStatus = applyStatus(body, withTitle);
  if (!withStatus) return { ok: false, code: "INVALID_STATUS" };

  const withArea = applyArea(body, withStatus);
  if (!withArea) return { ok: false, code: "INVALID_AREA" };

  return { ok: true, task: withArea };
}

function applyTitle(body: Record<string, unknown>, task: Task): Task | null {
  if (typeof body["title"] !== "string" && typeof body["description"] !== "string") {
    return task;
  }

  const title = typeof body["title"] === "string" ? body["title"].trim() : task.title;
  const description =
    typeof body["description"] === "string" ? body["description"] : task.description;
  if (!isTaskTitleValid(title)) return null;
  return { ...task, title, description };
}

function applyStatus(body: Record<string, unknown>, task: Task): Task | null {
  if (!("status" in body)) return task;
  if (!isTaskStatus(body["status"])) return null;
  const changed = changeTaskStatus(task, body["status"]);
  return changed.ok ? changed.value : null;
}

function applyArea(body: Record<string, unknown>, task: Task): Task | null {
  if (!("area" in body)) return task;
  if (!isTaskArea(body["area"])) return null;
  const changed = changeTaskArea(task, body["area"]);
  return changed.ok ? changed.value : null;
}

app.get("/", (c) => c.text("ok"));

app.get("/api/tasks", async (c) => {
  const result = await repository(c).list();
  if (!result.ok) return problem(c, 500, result.error.code);
  return c.json(result.value);
});

app.get("/api/tasks/:id", async (c) => {
  const result = await repository(c).find(c.req.param("id"), "local");
  if (!result.ok) return problem(c, 500, result.error.code);
  if (!result.value) return problem(c, 404, "NOT_FOUND");
  return c.json(result.value);
});

app.post("/api/tasks", async (c) => {
  const body = await c.req.json<Record<string, unknown>>();
  const title = typeof body["title"] === "string" ? body["title"].trim() : "";
  const description = typeof body["description"] === "string" ? body["description"] : "";

  if (!isTaskTitleValid(title)) {
    return problem(c, 400, "INVALID_TITLE");
  }

  const created = createTask({ owner_id: "local", title, description });
  if (!created.ok) return problem(c, 400, created.error.code);

  const inserted = await repository(c).insert(created.value);
  if (!inserted.ok) return problem(c, 500, inserted.error.code);

  c.header("Location", `/api/tasks/${inserted.value.id}`);
  return c.json(inserted.value, 201);
});

app.patch("/api/tasks/:id", async (c) => {
  const body = await c.req.json<Record<string, unknown>>();
  const found = await repository(c).find(c.req.param("id"), "local");
  if (!found.ok) return problem(c, 500, found.error.code);
  if (!found.value) return problem(c, 404, "NOT_FOUND");

  const patched = applyPatch(body, found.value);
  if (!patched.ok) return problem(c, 400, patched.code);
  const task = patched.task;

  const version = parseVersion(body["version"]);
  if (version === null) {
    return problem(c, 400, "INVALID_ORDER");
  }

  const updated = await repository(c).update({ ...task, version });
  if (!updated.ok) return problem(c, 409, updated.error.code);
  return c.json(updated.value);
});

app.post("/api/tasks/reorder", async (c) => {
  const body = await c.req.json<Record<string, unknown>>();
  const id = typeof body["id"] === "string" ? body["id"] : "";
  const version = parseVersion(body["version"]);
  const area = body["area"];
  const order = body["order"];
  if (
    !isTaskArea(area) ||
    typeof order !== "number" ||
    !Number.isInteger(order) ||
    version === null
  ) {
    return problem(c, 400, "INVALID_ORDER");
  }

  const listed = await repository(c).list();
  if (!listed.ok) return problem(c, 500, listed.error.code);

  const tasks = listed.value;
  const moved = moveTask(tasks, id, area, order);
  if (!moved.ok) return problem(c, 400, moved.error.code);

  const changed = moved.value.filter((task) => {
    const before = tasks.find((candidate) => candidate.id === task.id);
    return before !== undefined && (before.area !== task.area || before.order !== task.order);
  });
  const changedWithVersion = changed.map((task) => (task.id === id ? { ...task, version } : task));

  const result = await repository(c).move(changedWithVersion);
  if (!result.ok) return problem(c, 409, result.error.code);

  const saved = result.value.find((task) => task.id === id);
  return c.json(saved);
});

export default app;
