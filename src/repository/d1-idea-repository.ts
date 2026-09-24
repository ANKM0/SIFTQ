import type { D1Database, D1Result } from "@cloudflare/workers-types";
import { err, ok } from "../task";
import type { Result } from "../task";
import type { Idea } from "../idea";
import type { IdeaOrderUpdate, IdeaRepository, IdeaRepositoryError } from "./idea-repository";

function toIdea(value: unknown): Idea | undefined {
  if (typeof value !== "object" || value === null) return undefined;
  if (!isRecord(value)) return undefined;
  const row = value;
  if (
    typeof row["id"] !== "string" ||
    typeof row["owner_id"] !== "string" ||
    typeof row["title"] !== "string" ||
    typeof row["description"] !== "string" ||
    typeof row["order"] !== "number" ||
    (row["pinned"] !== 0 && row["pinned"] !== 1)
  ) return undefined;
  return {
    id: row["id"],
    owner_id: row["owner_id"],
    title: row["title"],
    description: row["description"],
    order: row["order"],
    pinned: row["pinned"] === 1,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function changes(result: D1Result): number {
  return result.meta?.changes ?? 0;
}

const SELECT = 'SELECT id, owner_id, title, description, "order", pinned FROM ideas';

export function createD1IdeaRepository(db: D1Database): IdeaRepository {
  return {
    list: (owner_id) => listIdeas(db, owner_id),
    find: (id, owner_id) => findIdea(db, id, owner_id),
    insert: (idea) => insertIdea(db, idea),
    update: (idea) => updateIdea(db, idea),
    remove: (id, owner_id) => removeIdea(db, id, owner_id),
    move: (owner_id, updates) => moveIdeas(db, owner_id, updates),
  };
}

async function listIdeas(db: D1Database, owner_id: string): Promise<Result<Idea[], IdeaRepositoryError>> {
  const result = await db
    .prepare(`${SELECT} WHERE owner_id = ? ORDER BY pinned DESC, "order" ASC, id ASC`)
    .bind(owner_id)
    .all<Record<string, unknown>>();
  return ok(result.results.map(toIdea).filter((idea): idea is Idea => idea !== undefined));
}

async function findIdea(
  db: D1Database,
  id: string,
  owner_id: string,
): Promise<Result<Idea | undefined, IdeaRepositoryError>> {
  const row = await db.prepare(`${SELECT} WHERE id = ? AND owner_id = ?`).bind(id, owner_id).first<Record<string, unknown>>();
  return ok(row === null ? undefined : toIdea(row));
}

async function insertIdea(db: D1Database, idea: Idea): Promise<Result<Idea, IdeaRepositoryError>> {
  await db
    .prepare('INSERT INTO ideas (id, owner_id, title, description, "order", pinned) VALUES (?, ?, ?, ?, ?, ?)')
    .bind(idea.id, idea.owner_id, idea.title, idea.description, idea.order, idea.pinned ? 1 : 0)
    .run();
  return ok(idea);
}

async function updateIdea(db: D1Database, idea: Idea): Promise<Result<Idea, IdeaRepositoryError>> {
  const result = await db
    .prepare('UPDATE ideas SET title = ?, description = ?, "order" = ?, pinned = ? WHERE id = ? AND owner_id = ?')
    .bind(idea.title, idea.description, idea.order, idea.pinned ? 1 : 0, idea.id, idea.owner_id)
    .run();
  return changes(result) === 0 ? err({ code: "NOT_FOUND" }) : ok(idea);
}

async function removeIdea(db: D1Database, id: string, owner_id: string): Promise<Result<null, IdeaRepositoryError>> {
  const result = await db.prepare("DELETE FROM ideas WHERE id = ? AND owner_id = ?").bind(id, owner_id).run();
  return changes(result) === 0 ? err({ code: "NOT_FOUND" }) : ok(null);
}

async function moveIdeas(
  db: D1Database,
  owner_id: string,
  updates: readonly IdeaOrderUpdate[],
): Promise<Result<Idea[], IdeaRepositoryError>> {
  const current = await listIdeas(db, owner_id);
  if (!current.ok) return current;
  const byId = new Map(current.value.map((idea) => [idea.id, idea]));
  if (updates.some((update) => !byId.has(update.id))) return err({ code: "CONFLICT" });
  const results = await db.batch(
    updates.map((update) =>
      db.prepare('UPDATE ideas SET "order" = ? WHERE id = ? AND owner_id = ?').bind(update.order, update.id, owner_id),
    ),
  );
  if (results.some((result) => changes(result) === 0)) return err({ code: "CONFLICT" });
  return listIdeas(db, owner_id);
}
