import { readFileSync } from "node:fs";
import { describe, expect, it } from "vite-plus/test";
import { adapter, checkApiRoutes, checkMigrations, parseMigrations, type Model } from "./siftq-adapter";

const realModel: Model = JSON.parse(
  readFileSync(new URL("../../docs/requirements/assets/domain-model/domain-model.json", import.meta.url), "utf8"),
);

describe("siftq adapter", () => {
  it("passes on the current domain model", () => {
    const result = adapter({ model: realModel });
    expect(result.errors).toEqual([]);
  });

  it("parseMigrations collects columns from CREATE and ALTER", () => {
    const into: Record<string, Record<string, string>> = {};
    parseMigrations(
      `CREATE TABLE IF NOT EXISTS tasks (\n  id TEXT PRIMARY KEY,\n  "order" INTEGER NOT NULL\n);\nALTER TABLE tasks ADD COLUMN working INTEGER NOT NULL DEFAULT 0;`,
      into,
    );
    expect(into["tasks"]).toEqual({ id: "TEXT", order: "INTEGER", working: "INTEGER" });
  });

  it("checkMigrations detects a missing column", () => {
    const model: Model = {
      domains: { string: { kind: "primitive" } },
      entities: { tasks: { attributes: { id: { domain: "string" }, title: { domain: "string" } } } },
    };
    const errors = checkMigrations(model, { tasks: { id: "TEXT" } });
    expect(errors.some((e) => e.includes("title"))).toBe(true);
  });

  it("checkApiRoutes detects drift between model and routes", () => {
    const model: Model = {
      domains: { string: { kind: "primitive" } },
      entities: { tasks: { attributes: { id: { domain: "string" } } } },
      api: { tasks_list: { kind: "api", method: "GET", path: "/api/tasks" } },
    };
    expect(checkApiRoutes(model, ["GET /api/tasks"])).toEqual([]);
    expect(checkApiRoutes(model, ["GET /api/ghost"])).toHaveLength(2);
  });
});
