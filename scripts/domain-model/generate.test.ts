import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { describe, expect, it } from "vite-plus/test";
import {
  apiMapD2,
  check,
  flowD2,
  logicalD2,
  navD2,
  parseMigrations,
  patchSvgDimensions,
  physicalD2,
  readApiRoutes,
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
});

describe("domain model checks", () => {
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

describe("api model", () => {
  const base: Model = {
    domains: { string: { kind: "primitive" } },
    entities: { tasks: { attributes: { id: { domain: "string" } } } },
  };

  it("checkApi accepts routes that follow the conventions", () => {
    const model: Model = {
      ...base,
      api: {
        tasks_list: { kind: "api", method: "GET", path: "/api/tasks", operation: "list", entity: "tasks", success: 200 },
        tasks_create: { kind: "api", method: "POST", path: "/api/tasks", operation: "create", entity: "tasks", success: 201 },
        tasks_reorder: { kind: "api", method: "POST", path: "/api/tasks/reorder", operation: "reorder", entity: "tasks", success: 200 },
        html_login: { kind: "html", method: "POST", path: "/login", operation: "login", success: 302 },
      },
    };
    expect(check(model, { invariantIds: null }).errors).toEqual([]);
  });

  it("checkApi rejects CRUD verbs, wrong success status, and unknown entities", () => {
    const model: Model = {
      ...base,
      api: {
        bad: { kind: "api", method: "POST", path: "/api/tasks/create", operation: "create", entity: "missing", success: 200 },
        wrong: { kind: "api", method: "GET", path: "/api/tasks", operation: "list", success: 201 },
      },
    };
    const errors = check(model, { invariantIds: null }).errors;
    expect(errors.some((e) => e.includes("CRUD 動詞"))).toBe(true);
    expect(errors.some((e) => e.includes("entities に無い"))).toBe(true);
    expect(errors.some((e) => e.includes("success は GET"))).toBe(true);
  });

  it("checkApi enforces the path prefix per kind", () => {
    const model: Model = {
      ...base,
      api: {
        api_outside: { kind: "api", method: "GET", path: "/tasks", operation: "list", success: 200 },
        html_in_api: { kind: "html", method: "POST", path: "/api/tasks", operation: "create", success: 201 },
      },
    };
    const errors = check(model, { invariantIds: null }).errors;
    expect(errors.some((e) => e.includes("/api/ で始める"))).toBe(true);
    expect(errors.some((e) => e.includes("HTML UI endpoint"))).toBe(true);
  });

  it("check rejects navigation calls that reference an unknown api", () => {
    const model: Model = {
      ...base,
      screens: { P01: { name: "Matrix", entities: ["tasks"] } },
      navigation: [{ from: "P01", on: "dnd", to: "P01", call: "tasks_reorder" }],
    };
    const errors = check(model, { invariantIds: null }).errors;
    expect(errors.some((e) => e.includes("call は api に無い"))).toBe(true);
  });
});

describe("api call map rendering", () => {
  it("apiMapD2 links screens to endpoints, endpoints to entities, and initial-render GET", () => {
    const model: Model = {
      domains: { string: { kind: "primitive" } },
      entities: { tasks: { attributes: { id: { domain: "string" } } } },
      screens: {
        P01: { name: "Matrix", entities: ["tasks"], onLoad: "html_matrix_page" },
        P02: { name: "Task list", entities: ["tasks"] },
      },
      navigation: [
        { from: "P01", on: "Tasks 押下", to: "P02" },
        { from: "P01", on: "ドラッグ&ドロップ", to: "P01", call: "tasks_reorder" },
      ],
      api: {
        tasks_reorder: { kind: "api", method: "POST", path: "/api/tasks/reorder", operation: "reorder", entity: "tasks", success: 200 },
        html_matrix_page: { kind: "html", method: "GET", path: "/matrix", operation: "load", entity: "tasks", success: 200 },
      },
    };
    const out = apiMapD2(model);
    expect(out).toContain('P01 -> tasks_reorder: "ドラッグ&ドロップ"');
    expect(out).toContain("tasks_reorder -> tasks");
    expect(out).toContain('tasks_reorder: "POST /api/tasks/reorder"');
    expect(out).toContain("tasks: \"tasks\\n(エンティティ)\"");
    expect(out).toContain("legend:");
    expect(out).not.toContain("画面未使用");
    expect(out).toContain('P01 -> html_matrix_page: "初期表示"');
    expect(out).toContain("html_matrix_page -> tasks");
    expect(out).not.toContain('"参照"');
    expect(out).not.toContain("tasks_reorder -> P01");
    expect(out).not.toContain('P01 -> P02');
  });
});

describe("api call map unused grouping", () => {
  it("apiMapD2 groups endpoints that no screen calls under 画面未使用", () => {
    const model: Model = {
      domains: { string: { kind: "primitive" } },
      entities: { tasks: { attributes: { id: { domain: "string" } } } },
      screens: { P02: { name: "Task list", entities: ["tasks"], onLoad: "html_tasks_page" } },
      api: {
        html_tasks_page: { kind: "html", method: "GET", path: "/tasks", operation: "load", entity: "tasks", success: 200 },
        tasks_list: { kind: "api", method: "GET", path: "/api/tasks", operation: "list", entity: "tasks", success: 200 },
      },
    };
    const out = apiMapD2(model);
    expect(out).toContain('unused: "画面未使用（契約API）"');
    expect(out).toContain("unused.tasks_list -> tasks");
    expect(out).toContain('legend_unused: "画面未使用"');
    expect(out).toContain('P02 -> html_tasks_page: "初期表示"');
  });

  it("checkScreens rejects an onLoad that is not a known html GET", () => {
    const model: Model = {
      domains: { string: { kind: "primitive" } },
      entities: { tasks: { attributes: { id: { domain: "string" } } } },
      screens: {
        P01: { name: "Matrix", entities: ["tasks"], onLoad: "missing" },
        P02: { name: "Task list", entities: ["tasks"], onLoad: "tasks_reorder" },
      },
      api: {
        tasks_reorder: { kind: "api", method: "POST", path: "/api/tasks/reorder", operation: "reorder", entity: "tasks", success: 200 },
      },
    };
    const errors = check(model, { invariantIds: null }).errors;
    expect(errors.some((e) => e.includes("onLoad は api に無い"))).toBe(true);
    expect(errors.some((e) => e.includes("onLoad は html の GET"))).toBe(true);
  });
});

describe("api call map logical references", () => {
  it("apiMapD2 draws references as dashed edges and keeps them out of 画面未使用", () => {
    const model: Model = {
      domains: { string: { kind: "primitive" } },
      entities: { ideas: { attributes: { id: { domain: "string" } } } },
      screens: { P08: { name: "Idea list", entities: ["ideas"], onLoad: "html_ideas_page", references: ["ideas_list"] } },
      api: {
        html_ideas_page: { kind: "html", method: "GET", path: "/ideas", operation: "load", entity: "ideas", success: 200 },
        ideas_list: { kind: "api", method: "GET", path: "/api/ideas", operation: "list", entity: "ideas", success: 200 },
      },
    };
    const out = apiMapD2(model);
    expect(out).toContain('P08 -> ideas_list: "参照"');
    expect(out).toContain("style.stroke-dash: 4");
    expect(out).toContain("論理参照");
    expect(out).not.toContain('unused: "画面未使用（契約API）"');
  });

  it("checkScreens rejects references that are not a known api", () => {
    const model: Model = {
      domains: { string: { kind: "primitive" } },
      entities: { ideas: { attributes: { id: { domain: "string" } } } },
      screens: { P08: { name: "Idea list", entities: ["ideas"], references: ["missing"] } },
    };
    const errors = check(model, { invariantIds: null }).errors;
    expect(errors.some((e) => e.includes("references は api に無い"))).toBe(true);
  });
});

describe("api route drift", () => {
  const realModel: Model = JSON.parse(
    readFileSync(new URL("../../docs/requirements/assets/domain-model/domain-model.json", import.meta.url), "utf8"),
  );

  it("domain-model api matches the registered Hono routes", () => {
    const routes = readApiRoutes(new URL("../../src/routes/", import.meta.url));
    const declared = Object.values(realModel.api ?? {})
      .filter((op) => op.kind === "api")
      .map((op) => `${op.method} ${op.path}`)
      .sort();
    expect(routes).toEqual(declared);
  });

  it("check rejects api routes that drift from the source routes", () => {
    expect(realModel.api).toBeDefined();
    const errors = check(realModel, {
      invariantIds: null,
      apiRoutes: [...readApiRoutes(new URL("../../src/routes/", import.meta.url)), "GET /api/ghost"],
    }).errors;
    expect(errors.some((e) => e.includes("/api/ghost"))).toBe(true);
  });
});
