import { describe, expect, it } from "vitest";
import { D1TaskRepository } from "../src/task-repository";
import type { Task } from "../src/task";

type Database = ConstructorParameters<typeof D1TaskRepository>[0];
type Statement = ReturnType<Database["prepare"]>;
type Result = Awaited<ReturnType<Statement["run"]>>;
type AllResult<T> = { results: T[]; meta: { changes: number } };

function result(changes: number): Result {
  return { results: [], meta: { changes } };
}

function row(id: string, version: number): Record<string, unknown> {
  return { ...task(id, version) };
}

function task(id: string, version: number): Task {
  return {
    id,
    title: "task",
    description: "",
    status: "do",
    area: 1,
    order: 0,
    version,
  };
}

function isRows<T>(rows: unknown[]): rows is T[] {
  return Array.isArray(rows);
}

function isRow<T>(row: unknown): row is T {
  return typeof row === "object" && row !== null;
}

class FakeStatement implements Statement {
  constructor(
    private readonly runResult: Result,
    private readonly allRows: unknown[] = [],
    private readonly firstRow: unknown = null,
  ) {}

  bind(...values: unknown[]): Statement {
    if (values.length === 0) return new FakeStatement(result(0));
    return this;
  }

  async run(): Promise<Result> {
    return this.runResult;
  }

  async all<T>(): Promise<AllResult<T>> {
    if (isRows<T>(this.allRows)) {
      return { results: this.allRows, meta: { changes: 0 } };
    }
    return { results: [], meta: { changes: 0 } };
  }

  async first<T>(): Promise<T | null> {
    if (isRow<T>(this.firstRow)) {
      return this.firstRow;
    }
    return null;
  }
}

class FakeDatabase implements Database {
  constructor(
    private readonly runResults: Result[] = [],
    private readonly batchResults: Result[] = [],
    private readonly allRowsList: unknown[][] = [],
    private readonly firstRows: unknown[] = [],
  ) {}

  prepare(): Statement {
    return new FakeStatement(
      this.runResults.shift() ?? result(0),
      this.allRowsList.shift() ?? [],
      this.firstRows.shift() ?? null,
    );
  }

  async batch(statements: Statement[]): Promise<Result[]> {
    return statements.map(
      (_, index) => this.batchResults[index] ?? result(0),
    );
  }
}

describe("D1TaskRepository", () => {
  it("lists tasks mapped from D1 rows", async () => {
    const repository = new D1TaskRepository(
      new FakeDatabase([], [], [[row("a", 2)]]),
    );

    const tasks = await repository.list();

    expect(tasks).toEqual([task("a", 2)]);
  });

  it("finds a task by id from a D1 row", async () => {
    const repository = new D1TaskRepository(
      new FakeDatabase([], [], [], [row("a", 3)]),
    );

    const found = await repository.find("a");

    expect(found).toEqual(task("a", 3));
  });

  it("returns undefined when find matches no row", async () => {
    const repository = new D1TaskRepository(new FakeDatabase());

    const found = await repository.find("missing");

    expect(found).toBeUndefined();
  });

  it("inserts a task and returns it", async () => {
    const repository = new D1TaskRepository(new FakeDatabase([result(1)]));

    const inserted = await repository.insert(task("a", 1));

    expect(inserted).toEqual(task("a", 1));
  });

  it("increments version when an update changes one row", async () => {
    const repository = new D1TaskRepository(new FakeDatabase([result(1)]));

    const updated = await repository.update(task("a", 4));

    expect(updated).toEqual(task("a", 5));
  });

  it("returns conflict when an update changes no rows", async () => {
    const repository = new D1TaskRepository(new FakeDatabase([result(0)]));

    const updated = await repository.update(task("a", 4));

    expect(updated).toBe("conflict");
  });

  it("increments versions for every moved task", async () => {
    const repository = new D1TaskRepository(
      new FakeDatabase([], [result(1), result(1)]),
    );

    const moved = await repository.move([task("a", 1), task("b", 2)]);

    expect(moved).toEqual([task("a", 2), task("b", 3)]);
  });

  it("returns conflict when any moved task changes no rows", async () => {
    const repository = new D1TaskRepository(
      new FakeDatabase([], [result(1), result(0)]),
    );

    const moved = await repository.move([task("a", 1), task("b", 2)]);

    expect(moved).toBe("conflict");
  });
});
