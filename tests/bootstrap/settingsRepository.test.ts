import { DatabaseSync } from "node:sqlite";
import { afterEach, describe, expect, it } from "vitest";

import {
  createStartupSettingsRepository,
  type SettingsRepositoryHost
} from "../../src/bootstrap/settingsRepository";
import {
  SqliteSettingsRepository,
  type SqliteConnection,
  type SqliteRow,
  type SqliteValue
} from "../../src/adapters/sqliteSettingsRepository";
import { getDefaultAreaLabelSettings } from "../../src/domain/settings";

const openDatabases: DatabaseSync[] = [];

afterEach(() => {
  while (openDatabases.length > 0) {
    openDatabases.pop()?.close();
  }
});

describe("createStartupSettingsRepository", () => {
  it("restores saved area labels from SQLite", async () => {
    const connection = createConnection();
    const savedLabels = {
      do: "Now",
      schedule: "Later",
      delegate: "Assign",
      eliminate: "Drop",
      skipped: "Dismissed",
      done: "Finished"
    };

    await new SqliteSettingsRepository(connection).saveAreaLabels(savedLabels);

    const repository = createStartupSettingsRepository({
      siftqSqliteSettingsConnection: connection
    });

    await expect(repository.loadAreaLabels()).resolves.toEqual(savedLabels);
  });

  it("uses default area labels when SQLite has no saved labels", async () => {
    const repository = createStartupSettingsRepository({
      siftqSqliteSettingsConnection: createConnection()
    });

    await expect(repository.loadAreaLabels()).resolves.toEqual(
      getDefaultAreaLabelSettings()
    );
  });

  it("uses in-memory defaults when the host has no SQLite connection", async () => {
    const host: SettingsRepositoryHost = {};
    const repository = createStartupSettingsRepository(host);

    await expect(repository.loadAreaLabels()).resolves.toEqual(
      getDefaultAreaLabelSettings()
    );
  });
});

function createConnection(): SqliteConnection {
  const database = new DatabaseSync(":memory:");
  openDatabases.push(database);

  return new NodeSqliteConnection(database);
}

class NodeSqliteConnection implements SqliteConnection {
  constructor(private readonly database: DatabaseSync) {}

  async execute(sql: string, params: readonly SqliteValue[] = []): Promise<void> {
    if (params.length === 0) {
      this.database.exec(sql);
      return;
    }

    this.database.prepare(sql).run(...params);
  }

  async select<Row extends SqliteRow>(
    sql: string,
    params: readonly SqliteValue[] = []
  ): Promise<Row[]> {
    return this.database.prepare(sql).all(...params) as Row[];
  }

  async transaction<Result>(operation: () => Promise<Result>): Promise<Result> {
    this.database.exec("BEGIN IMMEDIATE");

    try {
      const result = await operation();
      this.database.exec("COMMIT");

      return result;
    } catch (error) {
      this.database.exec("ROLLBACK");
      throw error;
    }
  }
}
