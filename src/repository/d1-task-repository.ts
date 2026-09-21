import type { D1Database, D1PreparedStatement, D1Result } from "@cloudflare/workers-types";
import { changeTaskStatuses, err, isTaskArea, isTaskStatus, ok } from "../task";
import type { Result, Task, TaskStatus, TaskVersionInput } from "../task";
import { validateBulkTasks } from "./repository-validation";
import type { RepositoryError, TaskRepository } from "./task-repository";

const OWNER_ID = "local";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toTask(value: unknown): Task | undefined {
  if (!isRecord(value)) return undefined;

  const { id, owner_id, title, description, status, working, area, order, version, created_at, updated_at } =
    value;

  if (typeof id !== "string") return undefined;
  if (typeof owner_id !== "string") return undefined;
  if (typeof title !== "string") return undefined;
  if (typeof description !== "string") return undefined;
  if (!isTaskStatus(status)) return undefined;
  if (working !== 0 && working !== 1) return undefined;
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
    working: working === 1,
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

export function createD1TaskRepository(db: D1Database): TaskRepository {
  return {
    list: () => listTasks(db),
    find: (id, owner_id) => findTask(db, id, owner_id),
    insert: (task) => insertTask(db, task),
    update: (task) => updateTask(db, task),
    remove: (id, owner_id, version) => removeTask(db, id, owner_id, version),
    bulkUpdateStatus: (inputs, status) => bulkUpdateStatus(db, inputs, status),
    bulkRemove: (inputs) => bulkRemove(db, inputs),
    move: (tasks) => moveTasks(db, tasks),
  };
}

async function bulkUpdateStatus(
  db: D1Database,
  inputs: readonly TaskVersionInput[],
  status: TaskStatus,
): Promise<Result<Task[], RepositoryError>> {
  const current = await findBulkTasks(db, inputs);
  if (!current.ok) return current;

  const updatedAt = new Date().toISOString();
  const executed = await executeBulk(db, current.value, (task) =>
    db
      .prepare(
        "UPDATE tasks SET status = ?, version = version + 1, updated_at = ? WHERE id = ? AND owner_id = ? AND version = ?",
      )
      .bind(status, updatedAt, task.id, OWNER_ID, task.version),
  );
  if (!executed.ok) return executed;

  return changeTaskStatuses(current.value, status, updatedAt);
}

async function listTasks(db: D1Database): Promise<Result<Task[], RepositoryError>> {
  const result = await db
    .prepare(
      'SELECT id, owner_id, title, description, status, working, area, "order", version, created_at, updated_at FROM tasks WHERE owner_id = ? ORDER BY id',
    )
    .bind(OWNER_ID)
    .all<Record<string, unknown>>();

  return ok(result.results.map(toTask).filter((task): task is Task => task !== undefined));
}

async function findTask(
  db: D1Database,
  id: string,
  owner_id: string,
): Promise<Result<Task | undefined, RepositoryError>> {
  const row = await db
    .prepare(
      'SELECT id, owner_id, title, description, status, working, area, "order", version, created_at, updated_at FROM tasks WHERE id = ? AND owner_id = ?',
    )
    .bind(id, owner_id)
    .first<Record<string, unknown>>();

  return ok(row === null ? undefined : toTask(row));
}

async function insertTask(db: D1Database, task: Task): Promise<Result<Task, RepositoryError>> {
  await db
    .prepare(
      'INSERT INTO tasks (id, owner_id, title, description, status, working, area, "order", version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
    )
    .bind(
      task.id,
      OWNER_ID,
      task.title,
      task.description,
      task.status,
      task.working ? 1 : 0,
      task.area,
      task.order,
      task.version,
      task.created_at,
      task.updated_at,
    )
    .run();

  return ok(task);
}

async function updateTask(db: D1Database, task: Task): Promise<Result<Task, RepositoryError>> {
  const updatedAt = new Date().toISOString();
  const result = await db
    .prepare(
      'UPDATE tasks SET title = ?, description = ?, status = ?, working = ?, area = ?, "order" = ?, version = version + 1, updated_at = ? WHERE id = ? AND owner_id = ? AND version = ?',
    )
    .bind(
      task.title,
      task.description,
      task.status,
      task.working ? 1 : 0,
      task.area,
      task.order,
      updatedAt,
      task.id,
      OWNER_ID,
      task.version,
    )
    .run();

  if (changes(result) === 0) return err({ code: "CONFLICT" });
  return ok({ ...task, version: task.version + 1, updated_at: updatedAt });
}

async function bulkRemove(
  db: D1Database,
  inputs: readonly TaskVersionInput[],
): Promise<Result<null, RepositoryError>> {
  const current = await findBulkTasks(db, inputs);
  if (!current.ok) return current;

  const executed = await executeBulk(db, current.value, (task) =>
    db
      .prepare("DELETE FROM tasks WHERE id = ? AND owner_id = ? AND version = ?")
      .bind(task.id, OWNER_ID, task.version),
  );
  if (!executed.ok) return executed;
  return ok(null);
}

async function removeTask(
  db: D1Database,
  id: string,
  owner_id: string,
  version: number,
): Promise<Result<null, RepositoryError>> {
  const found = await findTask(db, id, owner_id);
  if (!found.ok) return err(found.error);
  if (!found.value) return err({ code: "NOT_FOUND" });
  if (found.value.version !== version) return err({ code: "CONFLICT" });

  const result = await db
    .prepare("DELETE FROM tasks WHERE id = ? AND owner_id = ? AND version = ?")
    .bind(id, owner_id, version)
    .run();

  if (changes(result) === 0) return err({ code: "CONFLICT" });
  return ok(null);
}

async function findBulkTasks(
  db: D1Database,
  inputs: readonly TaskVersionInput[],
): Promise<Result<Task[], RepositoryError>> {
  const placeholders = inputs.map(() => "?").join(", ");
  const result = await db
    .prepare(
      `SELECT id, owner_id, title, description, status, working, area, "order", version, created_at, updated_at FROM tasks WHERE owner_id = ? AND id IN (${placeholders})`,
    )
    .bind(OWNER_ID, ...inputs.map((input) => input.id))
    .all<Record<string, unknown>>();
  const found = result.results.map(toTask).filter((task): task is Task => task !== undefined);
  const byId = new Map(found.map((task) => [task.id, task]));
  const validated = validateBulkTasks(inputs, (id) => byId.get(id));
  return validated.ok ? validated : err(validated.error);
}

async function moveTasks(
  db: D1Database,
  tasks: readonly Task[],
): Promise<Result<Task[], RepositoryError>> {
  if (tasks.length === 0) return ok([]);

  const updatedAt = new Date().toISOString();
  const statements = tasks.map((task) =>
    db
      .prepare(
        'UPDATE tasks SET area = ?, "order" = ?, version = version + 1, updated_at = ? WHERE id = ? AND owner_id = ? AND version = ?',
      )
      .bind(task.area, task.order, updatedAt, task.id, OWNER_ID, task.version),
  );
  const results = await db.batch(statements);

  if (results.some((result) => changes(result) === 0)) return err({ code: "CONFLICT" });
  return ok(
    tasks.map((task) => ({
      ...task,
      version: task.version + 1,
      updated_at: updatedAt,
    })),
  );
}

async function executeBulk(
  db: D1Database,
  tasks: readonly Task[],
  prepare: (task: Task) => D1PreparedStatement,
): Promise<Result<null, RepositoryError>> {
  const results = await db.batch(tasks.map(prepare));
  if (results.some((result) => changes(result) === 0)) return err({ code: "CONFLICT" });
  return ok(null);
}
