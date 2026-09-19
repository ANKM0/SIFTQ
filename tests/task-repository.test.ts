import { describe, expect, it } from "vite-plus/test";
import type { D1Database, D1PreparedStatement, D1Result } from "@cloudflare/workers-types";
import { createMemoryTaskRepository } from "./helpers/memory-task-repository";
import { taskFixture } from "./helpers/task-fixture";
import { createD1TaskRepository } from "../src/repository/d1-task-repository";
import type { TaskRepository } from "../src/repository/task-repository";
import type { Task } from "../src/task";

type Execution = { query: string; values: readonly unknown[] };

function successResult<T>(results: T[], changes: number): D1Result<T> {
  return {
    success: true,
    results,
    meta: {
      duration: 0,
      size_after: 0,
      rows_read: 0,
      rows_written: 0,
      last_row_id: 0,
      changed_db: changes > 0,
      changes,
    },
  };
}

interface StatementRecorder {
  record(query: string, values: readonly unknown[]): void;
  nextChanges(): number;
}

class RecordingPreparedStatement implements D1PreparedStatement {
  private values: readonly unknown[] = [];

  constructor(
    private readonly recorder: StatementRecorder,
    private readonly query: string,
  ) {}

  bind(...values: unknown[]): D1PreparedStatement {
    this.values = values;
    return this;
  }

  first<T = Record<string, unknown>>(_colName?: string): Promise<T | null> {
    return Promise.reject(new Error("first is not implemented in this test double"));
  }

  run<T = Record<string, unknown>>(): Promise<D1Result<T>> {
    this.recordExecution();
    return Promise.resolve(successResult<T>([], this.recorder.nextChanges()));
  }

  recordExecution(): void {
    this.recorder.record(this.query, this.values);
  }

  all<T = Record<string, unknown>>(): Promise<D1Result<T>> {
    return Promise.reject(new Error("all is not implemented in this test double"));
  }

  raw<T = unknown[]>(
    _options: { columnNames: true },
  ): Promise<[string[], ...T[]]>;
  raw<T = unknown[]>(_options?: { columnNames?: false }): Promise<T[]>;
  raw<T = unknown[]>(_options?: { columnNames?: boolean }): Promise<T[]> {
    return Promise.reject(new Error("raw is not implemented in this test double"));
  }
}

class RecordingD1Database implements D1Database, StatementRecorder {
  readonly executions: Execution[] = [];
  private readonly prepared: RecordingPreparedStatement[] = [];
  private changes: number[];

  constructor(changes: number[] = [1]) {
    this.changes = [...changes];
  }

  prepare(query: string): D1PreparedStatement {
    const statement = new RecordingPreparedStatement(this, query);
    this.prepared.push(statement);
    return statement;
  }

  batch<T = unknown>(statements: D1PreparedStatement[]): Promise<D1Result<T>[]> {
    const batch = this.prepared.slice(-statements.length);
    for (const statement of batch) {
      statement.recordExecution();
    }
    return Promise.resolve(batch.map(() => successResult<T>([], this.nextChanges())));
  }

  exec(): Promise<never> {
    return Promise.reject(new Error("exec is not implemented in this test double"));
  }

  withSession(): never {
    throw new Error("withSession is not implemented in this test double");
  }

  dump(): Promise<never> {
    return Promise.reject(new Error("dump is not implemented in this test double"));
  }

  record(query: string, values: readonly unknown[]): void {
    this.executions.push({ query, values: [...values] });
  }

  nextChanges(): number {
    return this.changes.shift() ?? 1;
  }
}

function expectInsertExecution(execution: Execution | undefined, task: Task): void {
  expect(execution?.query).toContain("INSERT INTO tasks");
  expect(execution?.values).toEqual([
    task.id,
    "local",
    task.title,
    task.description,
    task.status,
    0,
    task.area,
    task.order,
    task.version,
    task.created_at,
    task.updated_at,
  ]);
}

const unusedD1Database = {
  prepare() {
    throw new Error("D1 is not used by this factory contract test.");
  },
  batch() {
    throw new Error("D1 is not used by this factory contract test.");
  },
  exec() {
    throw new Error("D1 is not used by this factory contract test.");
  },
  withSession() {
    throw new Error("D1 is not used by this factory contract test.");
  },
  dump() {
    throw new Error("D1 is not used by this factory contract test.");
  },
} satisfies D1Database;

const repositoryMethods = ["bulkRemove", "bulkUpdateStatus", "find", "insert", "list", "move", "remove", "update"];

describe("TaskRepository contract", () => {
  it("inserts and reads a task through the in-memory double", async () => {
    const repository = createMemoryTaskRepository();
    const task = taskFixture({ id: "task-1" });

    const inserted = await repository.insert(task);
    const listed = await repository.list();

    expect(inserted.ok).toBe(true);
    expect(listed.ok).toBe(true);
    if (!inserted.ok || !listed.ok) return;
    expect(inserted.value.id).toBe("task-1");
    expect(listed.value.map((item) => item.id)).toContain("task-1");
  });

  it("exposes the contract from both repository factories", () => {
    const repositories: TaskRepository[] = [
      createMemoryTaskRepository(),
      createD1TaskRepository(unusedD1Database),
    ];

    for (const repository of repositories) {
      expect(Object.keys(repository).sort()).toEqual(repositoryMethods);
    }
  });

  it("maps inserts through the D1 adapter", async () => {
    const database = new RecordingD1Database([1, 1]);
    const repository = createD1TaskRepository(database);
    const task = taskFixture({ id: "task-1", version: 1 });

    const inserted = await repository.insert(task);

    expect(inserted.ok).toBe(true);
    expect(database.executions).toHaveLength(1);
    expectInsertExecution(database.executions[0], task);
  });

  it("maps updates through the D1 adapter", async () => {
    const database = new RecordingD1Database([1]);
    const repository = createD1TaskRepository(database);
    const task = taskFixture({ id: "task-1", version: 1 });

    const updated = await repository.update(task);

    expect(updated.ok).toBe(true);
    expect(database.executions[0]?.query).toContain("UPDATE tasks SET title");
  });

  it("returns conflicts from failed D1 updates and atomic moves", async () => {
    const updateDatabase = new RecordingD1Database([0]);
    const updateRepository = createD1TaskRepository(updateDatabase);
    const task = taskFixture({ id: "task-1", version: 1 });

    const updated = await updateRepository.update(task);

    expect(updated).toEqual({ ok: false, error: { code: "CONFLICT" } });

    const moveDatabase = new RecordingD1Database([1, 0]);
    const moveRepository = createD1TaskRepository(moveDatabase);
    const moved = await moveRepository.move([
      taskFixture({ id: "task-1", version: 1, area: 1 }),
      taskFixture({ id: "task-2", version: 1, area: 2 }),
    ]);

    expect(moved).toEqual({ ok: false, error: { code: "CONFLICT" } });
    expect(moveDatabase.executions).toHaveLength(2);
    expect(moveDatabase.executions.every(({ query }) => query.includes("UPDATE tasks SET area"))).toBe(true);
  });
});
