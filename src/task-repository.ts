import { isTaskArea, isTaskStatus } from "./task";
import type { Task } from "./task";

const OWNER_ID = "local";

interface TaskD1Result<T = unknown> {
  results: T[];
  meta: { changes: number };
}

interface TaskPreparedStatement {
  bind(...values: unknown[]): TaskPreparedStatement;
  run(): Promise<TaskD1Result>;
  all<T>(): Promise<TaskD1Result<T>>;
  first<T>(): Promise<T | null>;
}

interface TaskDatabase {
  prepare(query: string): TaskPreparedStatement;
  batch(statements: TaskPreparedStatement[]): Promise<TaskD1Result[]>;
}

export interface TaskRepository {
  list(): Promise<Task[]>;
  find(id: string): Promise<Task | undefined>;
  insert(task: Task): Promise<Task>;
  update(task: Task): Promise<Task | "conflict">;
  move(tasks: readonly Task[]): Promise<Task[] | "conflict">;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toTask(value: unknown): Task | undefined {
  if (!isRecord(value)) return undefined;

  const { id, title, description, status, area, order, version } = value;
  if (typeof id !== "string") return undefined;
  if (typeof title !== "string") return undefined;
  if (typeof description !== "string") return undefined;
  if (!isTaskStatus(status)) return undefined;
  if (!isTaskArea(area)) return undefined;
  if (typeof order !== "number") return undefined;
  if (typeof version !== "number") return undefined;

  return { id, title, description, status, area, order, version };
}

export class D1TaskRepository implements TaskRepository {
  constructor(private readonly db: TaskDatabase) {}

  async list(): Promise<Task[]> {
    const result = await this.db
      .prepare(
        'SELECT id, title, description, status, area, "order", version FROM tasks WHERE owner_id = ? ORDER BY id',
      )
      .bind(OWNER_ID)
      .all<Record<string, unknown>>();

    return result.results
      .map(toTask)
      .filter((task): task is Task => task !== undefined);
  }

  async find(id: string): Promise<Task | undefined> {
    const row = await this.db
      .prepare(
        'SELECT id, title, description, status, area, "order", version FROM tasks WHERE id = ? AND owner_id = ?',
      )
      .bind(id, OWNER_ID)
      .first<Record<string, unknown>>();

    return row === null ? undefined : toTask(row);
  }

  async insert(task: Task): Promise<Task> {
    await this.db
      .prepare(
        'INSERT INTO tasks (id, owner_id, title, description, status, area, "order", version) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
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
      )
      .run();

    return task;
  }

  async update(task: Task): Promise<Task | "conflict"> {
    const result = await this.db
      .prepare(
        'UPDATE tasks SET title = ?, description = ?, status = ?, area = ?, "order" = ?, version = version + 1 WHERE id = ? AND owner_id = ? AND version = ?',
      )
      .bind(
        task.title,
        task.description,
        task.status,
        task.area,
        task.order,
        task.id,
        OWNER_ID,
        task.version,
      )
      .run();

    if ((result.meta.changes ?? 0) === 0) return "conflict";
    return { ...task, version: task.version + 1 };
  }

  async move(tasks: readonly Task[]): Promise<Task[] | "conflict"> {
    if (tasks.length === 0) return [];

    const statements = tasks.map((task) =>
      this.db
        .prepare(
          'UPDATE tasks SET area = ?, "order" = ?, version = version + 1 WHERE id = ? AND owner_id = ? AND version = ?',
        )
        .bind(task.area, task.order, task.id, OWNER_ID, task.version),
    );
    const results = await this.db.batch(statements);

    if (results.some((result) => (result.meta.changes ?? 0) === 0)) {
      return "conflict";
    }
    return tasks.map((task) => ({ ...task, version: task.version + 1 }));
  }
}
