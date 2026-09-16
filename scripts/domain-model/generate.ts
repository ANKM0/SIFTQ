import { readFileSync, readdirSync, mkdirSync, writeFileSync, existsSync } from "node:fs";
import Ajv from "ajv";

export type Domain = { kind: string; logical?: string; values?: (string | number)[] };
export type Attribute = { domain: string; pk?: boolean; note?: string; rules?: string[] };
export type Transition = { on: string; domain?: string; from: string | string[]; to: string };
export type Entity = {
  description?: string;
  table?: string;
  attributes: Record<string, Attribute>;
  transitions?: Transition[];
  rules?: string[];
};
export type Relation = { from: string; to: string; kind: string; on?: string };
export type Step = {
  name: string;
  entity?: string;
  changes?: Record<string, string | number | boolean | (string | number | boolean)[]>;
  when?: string;
};
export type Flow = { name: string; actor?: string; steps: Step[] };
export type Screen = { name: string; entities: string[]; actions?: string[] };
export type NavigationItem = { from: string; on: string; to: string };
export type Model = {
  domains: Record<string, Domain>;
  entities: Record<string, Entity>;
  relations?: Relation[];
  flows?: Record<string, Flow>;
  screens?: Record<string, Screen>;
  navigation?: NavigationItem[];
};
export type Migrations = Record<string, Record<string, string>>;

export const LOGICAL_TO_DB: Record<string, string> = {
  string: "TEXT",
  boolean: "INTEGER",
  number: "INTEGER",
  datetime: "TEXT",
};

export function tableName(key: string, entity: Entity): string {
  return entity.table ?? key;
}

export function logicalType(model: Model, domain: string): string {
  const d = model.domains[domain];
  if (d === undefined) return domain;
  return d.kind === "primitive" ? domain : (d.logical ?? "string");
}

export function dbType(model: Model, domain: string): string {
  return LOGICAL_TO_DB[logicalType(model, domain)] ?? "TEXT";
}

export function validate(model: unknown, schema: object): string[] {
  const ajv = new Ajv({ allErrors: true, allowUnionTypes: true });
  const check = ajv.compile(schema);
  if (check(model)) return [];
  return (check.errors ?? []).map((e) => `${e.instancePath || "/"} ${e.message ?? ""}`.trim());
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
      const name = col?.[1];
      const type = col?.[2];
      if (name === undefined || type === undefined) continue;
      columns[name] = type.toUpperCase();
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

export type CheckInput = {
  invariantIds: string[] | null;
  testIds?: string[];
  migrations?: Migrations;
};

function checkAttributeDomains(model: Model): string[] {
  const errors: string[] = [];
  for (const [name, entity] of Object.entries(model.entities)) {
    for (const [attr, a] of Object.entries(entity.attributes)) {
      if (!(a.domain in model.domains)) {
        errors.push(`entities.${name}.attributes.${attr}.domain は domains に無い: ${a.domain}`);
      }
    }
  }
  return errors;
}

function transitionErrors(name: string, t: Transition, model: Model, domain: string): string[] {
  const values = model.domains[domain]?.values ?? [];
  const errors: string[] = [];
  for (const endpoint of [t.from].flat()) {
    if (!values.includes(endpoint)) {
      errors.push(`entities.${name}.transitions "${t.on}" の from=${endpoint} は domains.${domain}.values に無い`);
    }
  }
  if (!values.includes(t.to)) {
    errors.push(`entities.${name}.transitions "${t.on}" の to=${t.to} は domains.${domain}.values に無い`);
  }
  return errors;
}

function checkTransitions(model: Model): { errors: string[]; warnings: string[] } {
  const errors: string[] = [];
  const warnings: string[] = [];
  for (const [name, entity] of Object.entries(model.entities)) {
    for (const t of entity.transitions ?? []) {
      if (t.domain === undefined) {
        warnings.push(`entities.${name}.transitions "${t.on}" に domain が無く端点を検証できない`);
        continue;
      }
      errors.push(...transitionErrors(name, t, model, t.domain));
    }
  }
  return { errors, warnings };
}

function checkRelations(model: Model): string[] {
  const errors: string[] = [];
  for (const r of model.relations ?? []) {
    if (!(r.from in model.entities)) errors.push(`relations.from は entities に無い: ${r.from}`);
    if (!(r.to in model.entities)) errors.push(`relations.to は entities に無い: ${r.to}`);
  }
  return errors;
}

function checkFlowStep(model: Model, flowId: string, step: Step): string[] {
  if (step.entity === undefined || step.changes === undefined) return [];
  if (!(step.entity in model.entities)) {
    return [`flows.${flowId} の step "${step.name}" の entity は entities に無い: ${step.entity}`];
  }
  const attrs = model.entities[step.entity]?.attributes ?? {};
  const errors: string[] = [];
  for (const key of Object.keys(step.changes)) {
    if (!(key in attrs)) {
      errors.push(`flows.${flowId} の step "${step.name}" の changes.${key} は entities.${step.entity}.attributes に無い`);
    }
  }
  return errors;
}

function checkFlows(model: Model): string[] {
  return Object.entries(model.flows ?? {}).flatMap(([flowId, flow]) =>
    flow.steps.flatMap((step) => checkFlowStep(model, flowId, step)),
  );
}

function checkScreens(model: Model): string[] {
  return Object.entries(model.screens ?? {}).flatMap(([id, screen]) =>
    screen.entities
      .filter((ref) => !(ref in model.entities))
      .map((ref) => `screens.${id}.entities は entities に無い: ${ref}`),
  );
}

function checkNavigation(model: Model): string[] {
  const screenKeys = new Set(Object.keys(model.screens ?? {}));
  const errors: string[] = [];
  for (const nav of model.navigation ?? []) {
    if (!screenKeys.has(nav.from)) errors.push(`navigation.from は screens に無い: ${nav.from}`);
    if (!screenKeys.has(nav.to)) errors.push(`navigation.to は screens に無い: ${nav.to}`);
  }
  return errors;
}

function checkUnreferencedEntities(model: Model): string[] {
  const referenced = new Set(Object.values(model.screens ?? {}).flatMap((s) => s.entities));
  return Object.keys(model.entities)
    .filter((key) => !referenced.has(key))
    .map((key) => `entity "${key}" を参照する screen が無い`);
}

function collectRuleIds(model: Model): Set<string> {
  const used = new Set<string>();
  for (const entity of Object.values(model.entities)) {
    for (const id of entity.rules ?? []) used.add(id);
    for (const a of Object.values(entity.attributes)) for (const id of a.rules ?? []) used.add(id);
  }
  return used;
}

function checkInvariantRules(model: Model, input: CheckInput): { errors: string[]; warnings: string[] } {
  const errors: string[] = [];
  const warnings: string[] = [];
  if (input.invariantIds === null) {
    warnings.push("domain.md に INV-TM-xxx が無いため rules の検証をスキップ");
    return { errors, warnings };
  }
  const known = new Set(input.invariantIds);
  const used = collectRuleIds(model);
  for (const id of used) if (!known.has(id)) errors.push(`rules の ID が domain.md に無い: ${id}`);
  for (const id of known) if (!used.has(id)) warnings.push(`domain.md の ${id} を参照する rules が無い`);

  const tests = new Set(input.testIds ?? []);
  for (const id of known) if (!tests.has(id)) warnings.push(`${id} を検証するテストが無い`);
  for (const id of tests) if (!known.has(id)) errors.push(`テストの ID が domain.md に無い: ${id}`);
  return { errors, warnings };
}

export function check(model: Model, input: CheckInput): { errors: string[]; warnings: string[] } {
  const transitions = checkTransitions(model);
  const rules = checkInvariantRules(model, input);
  const errors = [
    ...checkAttributeDomains(model),
    ...transitions.errors,
    ...checkRelations(model),
    ...checkFlows(model),
    ...checkScreens(model),
    ...checkNavigation(model),
    ...rules.errors,
  ];
  if (input.migrations !== undefined) errors.push(...checkMigrations(model, input.migrations));
  return { errors, warnings: [...transitions.warnings, ...checkUnreferencedEntities(model), ...rules.warnings] };
}

function tableD2(model: Model, typeOf: (domain: string) => string): string {
  const tables = Object.entries(model.entities)
    .map(([key, entity]) => {
      const cols = Object.entries(entity.attributes)
        .map(([attr, a]) => `  ${attr}: ${typeOf(a.domain)}${a.pk ? " {constraint: primary_key}" : ""}`)
        .join("\n");
      return `${tableName(key, entity)}: {\n  shape: sql_table\n${cols}\n}`;
    })
    .join("\n\n");

  const rels = (model.relations ?? [])
    .map((r) => {
      const from = tableName(r.from, model.entities[r.from] ?? { attributes: {} });
      const to = tableName(r.to, model.entities[r.to] ?? { attributes: {} });
      return `${from} -> ${to}: ${[r.on, r.kind].filter(Boolean).join(" ")}`;
    })
    .join("\n");

  return rels ? `${tables}\n\n${rels}\n` : `${tables}\n`;
}

export function logicalD2(model: Model): string {
  return tableD2(model, (domain) => logicalType(model, domain));
}

export function physicalD2(model: Model): string {
  return tableD2(model, (domain) => dbType(model, domain));
}

function stepLabel(step: Step): string {
  if (step.changes === undefined) return step.name;
  const changes = Object.entries(step.changes)
    .map(([k, v]) => `${k}=${Array.isArray(v) ? v.join("|") : v}`)
    .join(", ");
  return `${step.name}\\n${changes}`;
}

export function flowD2(model: Model): string {
  return Object.entries(model.flows ?? {})
    .map(([id, flow]) => {
      const nodes = flow.steps.map((s, i) => `  step_${id}_${i}: "${stepLabel(s)}"`).join("\n");
      const chain = flow.steps.map((_, i) => `step_${id}_${i}`).join(" -> ");
      return `flow_${id}: "${flow.name}" {\n${nodes}\n  ${chain}\n}`;
    })
    .join("\n\n");
}

export function navD2(model: Model): string {
  const screens = Object.entries(model.screens ?? {})
    .map(([id, screen]) => `${id}: "${id}\\n${screen.name}"`)
    .join("\n");
  const edges = (model.navigation ?? [])
    .map((n) => `${n.from} -> ${n.to}: "${n.on.replace(/"/g, "'")}"`)
    .join("\n");
  return `direction: right\n\n${screens}\n\n${edges}\n`;
}

function readInvariantIds(domainMd: URL): string[] | null {
  if (!existsSync(domainMd)) return null;
  const text = readFileSync(domainMd, "utf8");
  const ids = [...text.matchAll(/INV-TM-\d{3}/g)].map((m) => m[0]);
  return ids.length > 0 ? [...new Set(ids)] : null;
}

export function readInvariantTestIds(dir: URL): string[] {
  const ids = new Set<string>();
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const child = new URL(entry.name + (entry.isDirectory() ? "/" : ""), dir);
    if (entry.isDirectory()) {
      for (const id of readInvariantTestIds(child)) ids.add(id);
      continue;
    }
    if (!entry.name.endsWith(".test.ts")) continue;
    for (const m of readFileSync(child, "utf8").matchAll(/INV-TM-\d{3}/g)) ids.add(m[0]);
  }
  return [...ids];
}

export function readMigrations(dir: URL): Migrations {
  const migrations: Migrations = {};
  if (!existsSync(dir)) return migrations;
  for (const name of readdirSync(dir)) {
    if (name.endsWith(".sql")) parseMigrations(readFileSync(new URL(name, dir), "utf8"), migrations);
  }
  return migrations;
}

function main(): void {
  const modelPath = new URL("../../docs/requirements/assets/domain-model/domain-model.json", import.meta.url);
  const schemaPath = new URL("../../docs/requirements/assets/domain-model/domain-model.schema.json", import.meta.url);
  const outDir = new URL("../../docs/requirements/assets/domain-model/generated/", import.meta.url);

  const model: Model = JSON.parse(readFileSync(modelPath, "utf8"));
  const schema = JSON.parse(readFileSync(schemaPath, "utf8"));

  const schemaErrors = validate(model, schema);
  if (schemaErrors.length > 0) {
    console.error("domain-model.json が schema に違反:");
    for (const e of schemaErrors) console.error(`  - ${e}`);
    process.exit(1);
  }

  const { errors, warnings } = check(model, {
    invariantIds: readInvariantIds(new URL("../../docs/requirements/domain.md", import.meta.url)),
    testIds: readInvariantTestIds(new URL("../../tests/", import.meta.url)),
    migrations: readMigrations(new URL("../../migrations/", import.meta.url)),
  });
  for (const w of warnings) console.warn(`warn: ${w}`);
  if (errors.length > 0) {
    console.error("クロスチェック違反:");
    for (const e of errors) console.error(`  - ${e}`);
    process.exit(1);
  }

  mkdirSync(outDir, { recursive: true });
  const outputs: [string, string][] = [
    ["logical.d2", logicalD2(model)],
    ["physical.d2", physicalD2(model)],
    ["flow.d2", flowD2(model)],
    ["nav.d2", navD2(model)],
  ];
  for (const [name, content] of outputs) {
    writeFileSync(new URL(name, outDir), content);
    console.log(`wrote generated/${name}`);
  }
}

if (import.meta.main) main();
