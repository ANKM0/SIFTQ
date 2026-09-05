import type { D1Database, D1Result } from "@cloudflare/workers-types";
import { err, isTaskArea, isTaskStatus, ok } from "./task";
import type { DomainError, Result, Task } from "./task";

export type RepositoryError = DomainError;

const OWNER_ID = "local";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toTask(value: unknown): Task | undefined {
  if (!isRecord(value)) return undefined;

  const { id, owner_id, title, description, status, area, order, version, created_at, updated_at } =
    value;

  if (typeof id !== "string") return undefined;
  if (typeof owner_id !== "string") return undefined;
  if (typeof title !== "string") return undefined;
  if (typeof description !== "string") return undefined;
  if (!isTaskStatus(status)) return undefined;
  if (!isTaskArea(area)) return undefined;
  if (typeof order !== "number") return undefined;
  if (typeof version !== "number") return undefined;
  if (typeof created_at !== "string") return undefined;
  if (typeof updated_at !== "string") return undefined;

  return {
    id,
    owner_id,
    title,
    description,
    status,
    area,
    order,
    version,
    created_at,
    updated_at,
  };
}

function changes(result: D1Result): number {
  return result.meta?.changes ?? 0;
}

export interface TaskRepository {
  list(): Promise<Result<Task[], RepositoryError>>;
  find(id: string, owner_id: string): Promise<Result<Task | undefined, RepositoryError>>;
  insert(task: Task): Promise<Result<Task, RepositoryError>>;
  update(task: Task): Promise<Result<Task, RepositoryError>>;
  remove(id: string, owner_id: string, version: number): Promise<Result<null, RepositoryError>>;
  move(tasks: readonly Task[]): Promise<Result<Task[], RepositoryError>>;
}

export class D1TaskRepository implements TaskRepository {
  constructor(private readonly db: D1Database) {}

  async list(): Promise<Result<Task[], RepositoryError>> {
    const result = await this.db
      .prepare(
        'SELECT id, owner_id, title, description, status, area, "order", version, created_at, updated_at FROM tasks WHERE owner_id = ? ORDER BY id',
      )
      .bind(OWNER_ID)
      .all<Record<string, unknown>>();

    return ok(result.results.map(toTask).filter((task): task is Task => task !== undefined));
  }

  async find(id: string, owner_id: string): Promise<Result<Task | undefined, RepositoryError>> {
    const row = await this.db
      .prepare(
        'SELECT id, owner_id, title, description, status, area, "order", version, created_at, updated_at FROM tasks WHERE id = ? AND owner_id = ?',
      )
      .bind(id, owner_id)
      .first<Record<string, unknown>>();

    return ok(row === null ? undefined : toTask(row));
  }

  async insert(task: Task): Promise<Result<Task, RepositoryError>> {
    await this.db
      .prepare(
        'INSERT INTO tasks (id, owner_id, title, description, status, area, "order", version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
      )
      .bind(
        task.id,
        OWNER_ID,
        task.title,
        task.description,
        task.status,
        task.area,
        task.order,
        task.version,
        task.created_at,
        task.updated_at,
      )
      .run();

    return ok(task);
  }

  async update(task: Task): Promise<Result<Task, RepositoryError>> {
    const updatedAt = new Date().toISOString();
    const result = await this.db
      .prepare(
        'UPDATE tasks SET title = ?, description = ?, status = ?, area = ?, "order" = ?, version = version + 1, updated_at = ? WHERE id = ? AND owner_id = ? AND version = ?',
      )
      .bind(
        task.title,
        task.description,
        task.status,
        task.area,
        task.order,
        updatedAt,
        task.id,
        OWNER_ID,
        task.version,
      )
      .run();

    if (changes(result) === 0) {
      return err({ code: "CONFLICT" });
    }
    return ok({ ...task, version: task.version + 1, updated_at: updatedAt });
  }

  async remove(id: string, owner_id: string, version: number): Promise<Result<null, RepositoryError>> {
    const found = await this.find(id, owner_id);
    if (!found.ok) return err(found.error);
    if (!found.value) return err({ code: "NOT_FOUND" });
    if (found.value.version !== version) return err({ code: "CONFLICT" });

    const result = await this.db
      .prepare("DELETE FROM tasks WHERE id = ? AND owner_id = ? AND version = ?")
      .bind(id, owner_id, version)
      .run();

    if (changes(result) === 0) return err({ code: "CONFLICT" });
    return ok(null);
  }

  async move(tasks: readonly Task[]): Promise<Result<Task[], RepositoryError>> {
    if (tasks.length === 0) return ok([]);

    const updatedAt = new Date().toISOString();
    const statements = tasks.map((task) =>
      this.db
        .prepare(
          'UPDATE tasks SET area = ?, "order" = ?, version = version + 1, updated_at = ? WHERE id = ? AND owner_id = ? AND version = ?',
        )
        .bind(task.area, task.order, updatedAt, task.id, OWNER_ID, task.version),
    );
    const results = await this.db.batch(statements);

    if (results.some((result) => changes(result) === 0)) {
      return err({ code: "CONFLICT" });
    }
    return ok(
      tasks.map((task) => ({
        ...task,
        version: task.version + 1,
        updated_at: updatedAt,
      })),
    );
  }
}
