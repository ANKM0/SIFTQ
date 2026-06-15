import { DatabaseSync } from "node:sqlite";
import { afterEach, describe, expect, it } from "vitest";

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

describe("SqliteSettingsRepository", () => {
  it("loads default labels from an empty database", async () => {
    const repository = createRepository();

    await expect(repository.loadAreaLabels()).resolves.toEqual(
      getDefaultAreaLabelSettings()
    );
  });

  it("saves and reloads complete area labels", async () => {
    const repository = createRepository();
    const labels = {
      do: "Now",
      schedule: "Later",
      delegate: "Assign",
      eliminate: "Drop",
      skipped: "Dismissed",
      done: "Finished"
    };

    await repository.saveAreaLabels(labels);

    await expect(repository.loadAreaLabels()).resolves.toEqual(labels);
  });

  it("treats missing rows as defaults when loading a partially migrated database", async () => {
    const database = createDatabase();
    const connection = new NodeSqliteConnection(database);

    await connection.execute(`
      CREATE TABLE area_label_settings (
        area_id TEXT PRIMARY KEY NOT NULL,
        label TEXT NOT NULL CHECK (length(trim(label)) > 0)
      )`);
    await connection.execute(
      "INSERT INTO area_label_settings (area_id, label) VALUES (?, ?)",
      ["do", "Today"]
    );

    const repository = new SqliteSettingsRepository(connection);

    await expect(repository.loadAreaLabels()).resolves.toEqual({
      ...getDefaultAreaLabelSettings(),
      do: "Today"
    });
  });

  it("loads labels independently of SQLite row order", async () => {
    const database = createDatabase();
    const connection = new NodeSqliteConnection(database);

    await connection.execute(`
      CREATE TABLE area_label_settings (
        area_id TEXT PRIMARY KEY NOT NULL,
        label TEXT NOT NULL CHECK (length(trim(label)) > 0)
      )`);
    for (const [areaId, label] of [
      ["done", "Finished"],
      ["skipped", "Dismissed"],
      ["eliminate", "Drop"],
      ["delegate", "Assign"],
      ["schedule", "Later"],
      ["do", "Now"]
    ] as const) {
      await connection.execute(
        "INSERT INTO area_label_settings (area_id, label) VALUES (?, ?)",
        [areaId, label]
      );
    }

    const repository = new SqliteSettingsRepository(connection);

    await expect(repository.loadAreaLabels()).resolves.toEqual({
      do: "Now",
      schedule: "Later",
      delegate: "Assign",
      eliminate: "Drop",
      skipped: "Dismissed",
      done: "Finished"
    });
  });

  it("rejects invalid labels before changing stored settings", async () => {
    const repository = createRepository();
    const labels = {
      do: "Now",
      schedule: "Later",
      delegate: "Assign",
      eliminate: "Drop",
      skipped: "Dismissed",
      done: "Finished"
    };

    await repository.saveAreaLabels(labels);
    await expect(
      repository.saveAreaLabels({
        ...labels,
        done: "   "
      })
    ).rejects.toThrow("Area label must not be empty.");

    await expect(repository.loadAreaLabels()).resolves.toEqual(labels);
  });

  it("restores default labels by writing them to SQLite", async () => {
    const repository = createRepository();

    await repository.saveAreaLabels({
      do: "Now",
      schedule: "Later",
      delegate: "Assign",
      eliminate: "Drop",
      skipped: "Dismissed",
      done: "Finished"
    });

    await expect(repository.restoreDefaultAreaLabels()).resolves.toEqual(
      getDefaultAreaLabelSettings()
    );
    await expect(repository.loadAreaLabels()).resolves.toEqual(
      getDefaultAreaLabelSettings()
    );
  });
});

function createRepository(): SqliteSettingsRepository {
  return new SqliteSettingsRepository(new NodeSqliteConnection(createDatabase()));
}

function createDatabase(): DatabaseSync {
  const database = new DatabaseSync(":memory:");
  openDatabases.push(database);

  return database;
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
