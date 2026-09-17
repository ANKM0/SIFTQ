import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { describe, expect, it } from "vite-plus/test";
import {
  check,
  flowD2,
  logicalD2,
  navD2,
  parseMigrations,
  patchSvgDimensions,
  physicalD2,
  validate,
  type Migrations,
  type Model,
} from "./generate";

const schema = JSON.parse(
  readFileSync(new URL("../../docs/requirements/assets/domain-model/domain-model.schema.json", import.meta.url), "utf8"),
);

const model: Model = {
  domains: {
    string: { kind: "primitive" },
    boolean: { kind: "primitive" },
    status: { kind: "state", logical: "string", values: ["do", "done", "skip"] },
  },
  entities: {
    tasks: {
      attributes: {
        id: { domain: "string", pk: true },
        status: { domain: "status", rules: ["INV-TM-001"] },
        working: { domain: "boolean" },
      },
      transitions: [{ on: "complete", domain: "status", from: "do", to: "done" }],
    },
  },
  flows: {
    task_management: {
      name: "タスクを管理する",
      steps: [{ name: "タスクを登録する", entity: "tasks", changes: { status: "do" } }],
    },
  },
  screens: { P01: { name: "Matrix", entities: ["tasks"] } },
  navigation: [{ from: "P01", on: "開く", to: "P01" }],
};

const migrations: Migrations = { tasks: { id: "TEXT", status: "TEXT", working: "INTEGER" } };

describe("domain model generation", () => {
  it("logicalD2 uses logical types", () => {
    const out = logicalD2(model);
    expect(out).toContain("id: string {constraint: primary_key}");
    expect(out).toContain("status: string");
    expect(out).toContain("working: boolean");
    expect(out).not.toContain("TEXT");
  });

  it("physicalD2 uses mapped D1 types", () => {
    const out = physicalD2(model);
    expect(out).toContain("id: TEXT {constraint: primary_key}");
    expect(out).toContain("status: TEXT");
    expect(out).toContain("working: INTEGER");
  });

  it("flowD2 and navD2 render the business flow and navigation", () => {
    expect(flowD2(model)).toContain("status=do");
    expect(navD2(model)).toContain("P01 -> P01");
  });

  it("parseMigrations collects columns from CREATE and ALTER", () => {
    const into: Migrations = {};
    parseMigrations(
      `CREATE TABLE IF NOT EXISTS tasks (\n  id TEXT PRIMARY KEY,\n  "order" INTEGER NOT NULL,\n  status TEXT NOT NULL CHECK (status IN ('do', 'done', 'skip'))\n);\nALTER TABLE tasks ADD COLUMN working INTEGER NOT NULL DEFAULT 0;`,
      into,
    );
    expect(into["tasks"]).toEqual({ id: "TEXT", order: "INTEGER", status: "TEXT", working: "INTEGER" });
  });

  it("check validates references, rules, and migrations", () => {
    const ok = check(model, { invariantIds: ["INV-TM-001"], testIds: ["INV-TM-001"], migrations });
    expect(ok.errors).toEqual([]);

    const current = migrations["tasks"] ?? {};
    const broken = check(model, {
      invariantIds: null,
      testIds: ["INV-TM-099"],
      migrations: { tasks: { ...current, working: "TEXT" } },
    });
    expect(broken.errors.some((e) => e.includes("mapping 期待"))).toBe(true);
    expect(broken.warnings.some((w) => w.includes("INV-TM"))).toBe(true);
  });

  it("check treats missing tests and orphan invariants as errors", () => {
    const result = check(model, {
      invariantIds: ["INV-TM-001", "INV-TM-002"],
      testIds: ["INV-TM-001"],
      migrations,
    });
    expect(result.errors.some((e) => e.includes("INV-TM-002") && e.includes("テスト"))).toBe(true);
    expect(result.errors.some((e) => e.includes("INV-TM-002") && e.includes("rules"))).toBe(true);
  });

  it("validate rejects schema violations", () => {
    expect(validate(model, schema)).toEqual([]);
    expect(validate({ entities: {} }, schema).length).toBeGreaterThan(0);
  });

  it("patchSvgDimensions adds width and height from the viewBox", () => {
    const dir = mkdtempSync(join(tmpdir(), "domain-model-"));
    try {
      const file = pathToFileURL(join(dir, "diagram.svg"));
      writeFileSync(file, `<svg viewBox="0 0 12 34"><svg width="12" height="34" viewBox="0 0 12 34"></svg></svg>`);
      patchSvgDimensions(file);
      expect(readFileSync(file, "utf8").startsWith(`<svg viewBox="0 0 12 34" width="12" height="34">`)).toBe(true);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
