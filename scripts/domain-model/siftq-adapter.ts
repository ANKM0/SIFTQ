import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

type Domain = { kind: string; logical?: string; values?: (string | number)[] };
type Attribute = { domain: string; pk?: boolean; rules?: string[] };
type Entity = { table?: string; attributes: Record<string, Attribute>; rules?: string[] };
type ApiOperation = { kind: string; method: string; path: string };
export type Model = {
  domains: Record<string, Domain>;
  entities: Record<string, Entity>;
  api?: Record<string, ApiOperation>;
};
type AdapterContext = { model: Model };
type AdapterResult = { errors?: string[]; warnings?: string[] };

type Migrations = Record<string, Record<string, string>>;

const LOGICAL_TO_DB: Record<string, string> = {
  string: "TEXT",
  boolean: "INTEGER",
  number: "INTEGER",
  datetime: "TEXT",
};

function tableName(key: string, entity: Entity): string {
  return entity.table ?? key;
}

function logicalType(model: Model, domain: string): string {
  const d = model.domains[domain];
  if (d === undefined) return domain;
  return d.kind === "primitive" ? domain : (d.logical ?? "string");
}

function dbType(model: Model, domain: string): string {
  return LOGICAL_TO_DB[logicalType(model, domain)] ?? "TEXT";
}

export function parseMigrations(sql: string, into: Migrations): void {
  const create = /CREATE TABLE (?:IF NOT EXISTS )?([a-z_]+)\s*\(([\s\S]*?)\)\s*;/gi;
  for (let m = create.exec(sql); m !== null; m = create.exec(sql)) {
    const table = m[1];
    const body = m[2];
    if (table === undefined || body === undefined) continue;
    const columns = (into[table] ??= {});
    for (const line of body.split("\n")) {
      const col = /^\s*"?([a-z_]+)"?\s+(TEXT|INTEGER|REAL|BLOB|NUMERIC)\b/i.exec(line);
      if (col?.[1] === undefined || col[2] === undefined) continue;
      columns[col[1]] = col[2].toUpperCase();
    }
  }
  const alter = /ALTER TABLE\s+([a-z_]+)\s+ADD COLUMN\s+"?([a-z_]+)"?\s+(TEXT|INTEGER|REAL|BLOB|NUMERIC)/gi;
  for (let m = alter.exec(sql); m !== null; m = alter.exec(sql)) {
    const table = m[1];
    const name = m[2];
    const type = m[3];
    if (table === undefined || name === undefined || type === undefined) continue;
    const columns = (into[table] ??= {});
    columns[name] = type.toUpperCase();
  }
}

export function checkMigrations(model: Model, migrations: Migrations): string[] {
  const errors: string[] = [];
  for (const [key, entity] of Object.entries(model.entities)) {
    const table = tableName(key, entity);
    const actual = migrations[table];
    if (actual === undefined) {
      errors.push(`migrations に table "${table}" が無い`);
      continue;
    }
    const expected = new Set<string>();
    for (const [attr, a] of Object.entries(entity.attributes)) {
      expected.add(attr);
      const want = dbType(model, a.domain);
      const got = actual[attr];
      if (got === undefined) errors.push(`migrations.${table} に列 "${attr}" が無い`);
      else if (got !== want) errors.push(`migrations.${table}.${attr} の型は ${got}。mapping 期待は ${want}`);
    }
    for (const col of Object.keys(actual)) {
      if (!expected.has(col)) errors.push(`migrations.${table} に余分な列 "${col}"`);
    }
  }
  return errors;
}

function collectRuleIds(model: Model): Set<string> {
  const used = new Set<string>();
  for (const entity of Object.values(model.entities)) {
    for (const id of entity.rules ?? []) used.add(id);
    for (const a of Object.values(entity.attributes)) for (const id of a.rules ?? []) used.add(id);
  }
  return used;
}

function checkInvariantRules(model: Model, invariantIds: string[] | null, testIds: string[]): AdapterResult {
  if (invariantIds === null) {
    return { warnings: ["domain.md に INV-TM-xxx が無いため rules の検証をスキップ"] };
  }
  const known = new Set(invariantIds);
  const used = collectRuleIds(model);
  const errors: string[] = [];
  for (const id of used) if (!known.has(id)) errors.push(`rules の ID が domain.md に無い: ${id}`);
  for (const id of known) if (!used.has(id)) errors.push(`domain.md の ${id} を参照する rules が無い`);
  const tests = new Set(testIds);
  for (const id of known) if (!tests.has(id)) errors.push(`${id} を検証するテストが無い`);
  for (const id of tests) if (!known.has(id)) errors.push(`テストの ID が domain.md に無い: ${id}`);
  return { errors };
}

export function checkApiRoutes(model: Model, routes: string[]): string[] {
  const declared = new Set(
    Object.values(model.api ?? {})
      .filter((op) => op.kind === "api")
      .map((op) => `${op.method} ${op.path}`),
  );
  const actual = new Set(routes);
  return [
    ...[...declared].filter((r) => !actual.has(r)).map((r) => `domain-model.json の api route が src/routes/*-api.ts に無い: ${r}`),
    ...[...actual].filter((r) => !declared.has(r)).map((r) => `src/routes/*-api.ts の route が domain-model.json の api に無い: ${r}`),
  ].sort();
}

function readInvariantIds(path: string): string[] | null {
  if (!existsSync(path)) return null;
  const ids = [...readFileSync(path, "utf8").matchAll(/INV-TM-\d{3}/g)].map((m) => m[0]);
  return ids.length > 0 ? [...new Set(ids)] : null;
}

function readInvariantTestIds(dir: string): string[] {
  const ids = new Set<string>();
  if (!existsSync(dir)) return [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const child = join(dir, entry.name);
    if (entry.isDirectory()) {
      for (const id of readInvariantTestIds(child)) ids.add(id);
      continue;
    }
    if (!entry.name.endsWith(".test.ts")) continue;
    for (const m of readFileSync(child, "utf8").matchAll(/INV-TM-\d{3}/g)) ids.add(m[0]);
  }
  return [...ids];
}

function readMigrations(dir: string): Migrations {
  const migrations: Migrations = {};
  if (!existsSync(dir)) return migrations;
  for (const name of readdirSync(dir)) {
    if (name.endsWith(".sql")) parseMigrations(readFileSync(join(dir, name), "utf8"), migrations);
  }
  return migrations;
}

function readApiRoutes(dir: string): string[] {
  const routes = new Set<string>();
  if (!existsSync(dir)) return [];
  for (const name of readdirSync(dir)) {
    if (!name.endsWith("-api.ts")) continue;
    for (const m of readFileSync(join(dir, name), "utf8").matchAll(/app\.(get|post|patch|delete|put)\("([^"]+)"/g)) {
      if (m[1] === undefined || m[2] === undefined) continue;
      routes.add(`${m[1].toUpperCase()} ${m[2].replace(/:([a-z]+)/g, "{$1}")}`);
    }
  }
  return [...routes].sort();
}

export const adapter = ({ model }: AdapterContext): AdapterResult => {
  const root = fileURLToPath(new URL("../../", import.meta.url));
  const rules = checkInvariantRules(model, readInvariantIds(join(root, "docs/requirements/domain.md")), readInvariantTestIds(join(root, "tests")));
  return {
    errors: [...(rules.errors ?? []), ...checkMigrations(model, readMigrations(join(root, "migrations"))), ...checkApiRoutes(model, readApiRoutes(join(root, "src/routes")))],
    warnings: rules.warnings ?? [],
  };
};
