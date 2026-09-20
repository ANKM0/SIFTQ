import type { Context, Hono } from "hono";
import type { ContentfulStatusCode } from "hono/utils/http-status";
import {
  changeTaskArea,
  changeTaskStatus,
  changeTaskWorking,
  createTask,
  err,
  isTaskArea,
  isTaskStatus,
  isTaskTitleValid,
  moveTask,
  ok,
  parseTaskVersionInputs,
} from "../task";
import type { DomainError, Result, Task } from "../task";
import type { TaskRepository } from "../repository/task-repository";
import { parseVersion } from "../task-input";

type ApiEnv = { Bindings: Record<string, unknown> };
type Repository<T extends ApiEnv> = (c: Context<T>) => TaskRepository;

function problem<T extends ApiEnv>(c: Context<T>, status: ContentfulStatusCode, code: string) {
  return c.json({ code }, status);
}

function bulkProblem<T extends ApiEnv>(c: Context<T>, code: string) {
  return problem(c, code === "NOT_FOUND" ? 404 : 409, code);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

async function readJsonRecord<T extends ApiEnv>(c: Context<T>): Promise<Record<string, unknown> | null> {
  try {
    const body = await c.req.json<unknown>();
    return isRecord(body) ? body : null;
  } catch {
    return null;
  }
}

function createTaskAtBoundary({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  const now = new Date().toISOString();
  return createTask({
    id: crypto.randomUUID(),
    owner_id: "local",
    title,
    description,
    created_at: now,
    updated_at: now,
  });
}

type ApiTaskLookup =
  | { ok: true; task: Task }
  | { ok: false; status: ContentfulStatusCode; code: string };

async function findApiTask<T extends ApiEnv>(repository: Repository<T>, c: Context<T>, id: string): Promise<ApiTaskLookup> {
  const found = await repository(c).find(id, "local");
  if (!found.ok) return { ok: false, status: 500, code: found.error.code };
  if (!found.value) return { ok: false, status: 404, code: "NOT_FOUND" };
  return { ok: true, task: found.value };
}

function applyPatch(body: Record<string, unknown>, task: Task): Result<Task, DomainError> {
  const withTitle = applyTitle(body, task);
  if (!withTitle.ok) return withTitle;
  const withStatus = applyStatus(body, withTitle.value);
  if (!withStatus.ok) return withStatus;
  const withArea = applyArea(body, withStatus.value);
  if (!withArea.ok) return withArea;
  return applyWorking(body, withArea.value);
}

function applyTitle(body: Record<string, unknown>, task: Task): Result<Task, DomainError> {
  if (typeof body["title"] !== "string" && typeof body["description"] !== "string") return ok(task);
  const title = typeof body["title"] === "string" ? body["title"].trim() : task.title;
  const description = typeof body["description"] === "string" ? body["description"] : task.description;
  if (!isTaskTitleValid(title)) return err({ code: "INVALID_TITLE" });
  return ok({ ...task, title, description });
}

function applyStatus(body: Record<string, unknown>, task: Task): Result<Task, DomainError> {
  if (!("status" in body)) return ok(task);
  if (!isTaskStatus(body["status"])) return err({ code: "INVALID_STATUS" });
  return changeTaskStatus(task, body["status"]);
}

function applyArea(body: Record<string, unknown>, task: Task): Result<Task, DomainError> {
  if (!("area" in body)) return ok(task);
  if (!isTaskArea(body["area"])) return err({ code: "INVALID_AREA" });
  return changeTaskArea(task, body["area"]);
}

function applyWorking(body: Record<string, unknown>, task: Task): Result<Task, DomainError> {
  if (!("working" in body)) return ok(task);
  if (typeof body["working"] !== "boolean") return err({ code: "INVALID_WORKING" });
  return changeTaskWorking(task, body["working"]);
}

function registerTaskCollectionRoutes<T extends ApiEnv>(app: Hono<T>, repository: Repository<T>) {
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
    if (!isTaskTitleValid(title)) return problem(c, 400, "INVALID_TITLE");
    const created = createTaskAtBoundary({ title, description });
    if (!created.ok) return problem(c, 400, created.error.code);
    const inserted = await repository(c).insert(created.value);
    if (!inserted.ok) return problem(c, 500, inserted.error.code);
    c.header("Location", `/api/tasks/${inserted.value.id}`);
    return c.json(inserted.value, 201);
  });

}

function registerTaskBulkRoutes<T extends ApiEnv>(app: Hono<T>, repository: Repository<T>) {
  app.patch("/api/tasks/bulk/status", async (c) => {
    const body = await readJsonRecord(c);
    if (body === null) return problem(c, 400, "INVALID_BULK_INPUT");
    const status = body["status"];
    const inputs = parseTaskVersionInputs(body["tasks"]);
    if (!isTaskStatus(status)) return problem(c, 400, "INVALID_STATUS");
    if (!inputs.ok) return problem(c, 400, inputs.error.code);
    const result = await repository(c).bulkUpdateStatus(inputs.value, status);
    if (!result.ok) return bulkProblem(c, result.error.code);
    return c.json(result.value);
  });

  app.delete("/api/tasks/bulk", async (c) => {
    const body = await readJsonRecord(c);
    if (body === null) return problem(c, 400, "INVALID_BULK_INPUT");
    const inputs = parseTaskVersionInputs(body["tasks"]);
    if (!inputs.ok) return problem(c, 400, inputs.error.code);
    const result = await repository(c).bulkRemove(inputs.value);
    if (!result.ok) return bulkProblem(c, result.error.code);
    return c.body(null, 204);
  });

}

function registerTaskItemRoutes<T extends ApiEnv>(app: Hono<T>, repository: Repository<T>) {
  app.patch("/api/tasks/:id", async (c) => {
    const body = await c.req.json<Record<string, unknown>>();
    const found = await findApiTask(repository, c, c.req.param("id"));
    if (!found.ok) return problem(c, found.status, found.code);
    const patched = applyPatch(body, found.task);
    if (!patched.ok) return problem(c, 400, patched.error.code);
    const version = parseVersion(body["version"]);
    if (version === null) return problem(c, 400, "INVALID_ORDER");
    const updated = await repository(c).update({ ...patched.value, version });
    if (!updated.ok) return problem(c, 409, updated.error.code);
    return c.json(updated.value);
  });

  app.delete("/api/tasks/:id", async (c) => {
    const body = await c.req.json<Record<string, unknown>>();
    const version = parseVersion(body["version"]);
    if (version === null) return problem(c, 400, "INVALID_ORDER");
    const found = await findApiTask(repository, c, c.req.param("id"));
    if (!found.ok) return problem(c, found.status, found.code);
    const removed = await repository(c).remove(found.task.id, "local", version);
    if (!removed.ok) {
      return removed.error.code === "CONFLICT"
        ? problem(c, 409, removed.error.code)
        : problem(c, 404, removed.error.code);
    }
    return c.body(null, 204);
  });

}

function registerTaskReorderRoute<T extends ApiEnv>(app: Hono<T>, repository: Repository<T>) {
  app.post("/api/tasks/reorder", async (c) => {
    const body = await c.req.json<Record<string, unknown>>();
    const id = typeof body["id"] === "string" ? body["id"] : "";
    const version = parseVersion(body["version"]);
    const area = body["area"];
    const order = body["order"];
    if (!isTaskArea(area) || typeof order !== "number" || !Number.isInteger(order) || version === null) {
      return problem(c, 400, "INVALID_ORDER");
    }
    const listed = await repository(c).list();
    if (!listed.ok) return problem(c, 500, listed.error.code);
    const moved = moveTask(listed.value, id, area, order);
    if (!moved.ok) return problem(c, 400, moved.error.code);
    const changed = moved.value.filter((task) => {
      const before = listed.value.find((candidate) => candidate.id === task.id);
      return before !== undefined && (before.area !== task.area || before.order !== task.order);
    });
    const changedWithVersion = changed.map((task) => (task.id === id ? { ...task, version } : task));
    const result = await repository(c).move(changedWithVersion);
    if (!result.ok) return problem(c, 409, result.error.code);
    return c.json(result.value);
  });
}

export function registerTaskApiRoutes<T extends ApiEnv>(app: Hono<T>, repository: Repository<T>) {
  registerTaskCollectionRoutes(app, repository);
  registerTaskBulkRoutes(app, repository);
  registerTaskItemRoutes(app, repository);
  registerTaskReorderRoute(app, repository);
}
