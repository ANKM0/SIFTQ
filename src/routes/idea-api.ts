import type { Context, Hono } from "hono";
import type { ContentfulStatusCode } from "hono/utils/http-status";
import { err, ok } from "../task";
import {
  isIdeaDescriptionValid,
  isIdeaRecord,
  isIdeaOrderValid,
  isIdeaTitleValid,
  type Idea,
} from "../idea";
import type { AppEnv } from "../app-env";
import type { IdeaOrderUpdate, IdeaRepository, IdeaRepositoryError } from "../repository/idea-repository";

const OWNER_ID = "local";
type Repository = (c: Context<AppEnv>) => IdeaRepository;

function problem(c: Context<AppEnv>, status: ContentfulStatusCode, code: string) {
  return c.json({ code }, status);
}

async function readJsonRecord(c: Context<AppEnv>): Promise<Record<string, unknown> | null> {
  try {
    const value = await c.req.json<unknown>();
    return isIdeaRecord(value) ? value : null;
  } catch {
    return null;
  }
}

function errorStatus(code: string): ContentfulStatusCode {
  if (code === "NOT_FOUND") return 404;
  if (code === "CONFLICT") return 409;
  return 400;
}

function readOrder(value: unknown): number | null {
  return typeof value === "number" && isIdeaOrderValid(value) ? value : null;
}

type IdeaLookup = { ok: true; value: Idea } | { ok: false; error: IdeaRepositoryError };

async function findIdea(c: Context<AppEnv>, repository: Repository, id: string): Promise<IdeaLookup> {
  const result = await repository(c).find(id, OWNER_ID);
  if (!result.ok) return result;
  return result.value === undefined ? { ok: false, error: { code: "NOT_FOUND" } } : { ok: true, value: result.value };
}

function patchIdea(body: Record<string, unknown>, idea: Idea) {
  const title = typeof body["title"] === "string" ? body["title"].trim() : idea.title;
  const description = typeof body["description"] === "string" ? body["description"] : idea.description;
  const pinned = typeof body["pinned"] === "boolean" ? body["pinned"] : idea.pinned;
  const order = body["order"] === undefined ? idea.order : readOrder(body["order"]);
  if (order === null) return err<Idea, { code: "INVALID_ORDER" }>({ code: "INVALID_ORDER" });
  if (!isIdeaTitleValid(title)) return err<Idea, { code: "INVALID_TITLE" }>({ code: "INVALID_TITLE" });
  if (!isIdeaDescriptionValid(description)) return err<Idea, { code: "INVALID_DESCRIPTION" }>({ code: "INVALID_DESCRIPTION" });
  return ok<Idea, never>({ ...idea, title, description, pinned, order });
}

export function registerIdeaApiRoutes(app: Hono<AppEnv>, repository: Repository) {
  app.get("/api/ideas", async (c) => {
    const result = await repository(c).list(OWNER_ID);
    if (!result.ok) return problem(c, 500, result.error.code);
    return c.json(result.value, 200);
  });

  app.post("/api/ideas", async (c) => {
    const body = await readJsonRecord(c);
    if (body === null) return problem(c, 400, "INVALID_INPUT");
    const title = typeof body["title"] === "string" ? body["title"].trim() : "";
    const description = typeof body["description"] === "string" ? body["description"] : "";
    if (!isIdeaTitleValid(title)) return problem(c, 400, "INVALID_TITLE");
    if (!isIdeaDescriptionValid(description)) return problem(c, 400, "INVALID_DESCRIPTION");
    const current = await repository(c).list(OWNER_ID);
    if (!current.ok) return problem(c, 500, current.error.code);
    const pinned = body["pinned"] === true;
    const order = current.value
      .filter((idea) => idea.pinned === pinned)
      .reduce((maximum, idea) => Math.max(maximum, idea.order), 0) + 1;
    const idea: Idea = { id: crypto.randomUUID(), owner_id: OWNER_ID, title, description, order, pinned };
    const inserted = await repository(c).insert(idea);
    if (!inserted.ok) return problem(c, errorStatus(inserted.error.code), inserted.error.code);
    return c.json(inserted.value, 201);
  });

  app.post("/api/ideas/reorder", async (c) => {
    const body = await readJsonRecord(c);
    const rawIdeas = body?.["ideas"];
    if (!Array.isArray(rawIdeas) || rawIdeas.length === 0) return problem(c, 400, "INVALID_INPUT");
    const updates: IdeaOrderUpdate[] = [];
    for (const rawIdea of rawIdeas) {
      if (!isIdeaRecord(rawIdea) || typeof rawIdea["id"] !== "string") return problem(c, 400, "INVALID_INPUT");
      const order = readOrder(rawIdea["order"]);
      if (order === null) return problem(c, 400, "INVALID_ORDER");
      updates.push({ id: rawIdea["id"], order });
    }
    const moved = await repository(c).move(OWNER_ID, updates);
    if (!moved.ok) return problem(c, errorStatus(moved.error.code), moved.error.code);
    return c.json(moved.value);
  });

  app.patch("/api/ideas/:id", async (c) => {
    const body = await readJsonRecord(c);
    if (body === null) return problem(c, 400, "INVALID_INPUT");
    const found = await findIdea(c, repository, c.req.param("id"));
    if (!found.ok) return problem(c, errorStatus(found.error.code), found.error.code);
    const patched = patchIdea(body, found.value);
    if (!patched.ok) return problem(c, 400, patched.error.code);
    const updated = await repository(c).update(patched.value);
    if (!updated.ok) return problem(c, errorStatus(updated.error.code), updated.error.code);
    return c.json(updated.value);
  });

  app.delete("/api/ideas/:id", async (c) => {
    const removed = await repository(c).remove(c.req.param("id"), OWNER_ID);
    if (!removed.ok) return problem(c, errorStatus(removed.error.code), removed.error.code);
    return c.body(null, 204);
  });
}
