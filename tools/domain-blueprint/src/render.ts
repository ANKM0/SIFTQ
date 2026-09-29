import type { ApiOperation, Model } from "./model.ts";

export type I18n = {
  legend: string;
  initial: string;
  reference: string;
  unused: string;
  entity: string;
  unusedTitle: string;
  referenceLegend: string;
  unusedLegend: string;
  entityLegend: string;
};

export const DEFAULT_I18N: I18n = {
  legend: "Legend",
  initial: "initial",
  reference: "reference",
  unused: "unused",
  entity: "entity",
  unusedTitle: "Unused endpoints",
  referenceLegend: "logical reference (not called)",
  unusedLegend: "unused",
  entityLegend: "entity (domain)",
};

export function tableName(key: string, entity: { table?: string }): string {
  return entity.table ?? key;
}

export function logicalType(model: Model, domain: string): string {
  const d = model.domains[domain];
  if (d === undefined) return domain;
  return d.kind === "primitive" ? domain : (d.logical ?? "string");
}

export function dbType(model: Model, domain: string, typeMap: Record<string, string>): string {
  const logical = logicalType(model, domain);
  return typeMap[logical] ?? logical;
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

export function physicalD2(model: Model, typeMap: Record<string, string>): string {
  return tableD2(model, (domain) => dbType(model, domain, typeMap));
}

function stepLabel(step: { name: string; changes?: Record<string, unknown> }): string {
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

const API_FILL = { api: "#e8f0ff", html: "#fdf3e3" } as const;
const UNUSED_FILL = "#eeeeee";

function endpointFill(op: ApiOperation): string {
  return op.kind === "html" ? API_FILL.html : API_FILL.api;
}

function endpointNode(id: string, op: ApiOperation, fill: string): string {
  return [`${id}: "${op.method} ${op.path}"`, `${id}.shape: parallelogram`, `${id}.style.fill: "${fill}"`].join("\n");
}

function indent(text: string): string {
  return text
    .split("\n")
    .map((line) => `  ${line}`)
    .join("\n");
}

function usedEndpointIds(model: Model): Set<string> {
  return new Set([
    ...(model.navigation ?? []).flatMap((n) => (n.call === undefined ? [] : [n.call])),
    ...Object.values(model.screens ?? {}).flatMap((s) => (s.onLoad === undefined ? [] : [s.onLoad])),
    ...Object.values(model.screens ?? {}).flatMap((s) => s.references ?? []),
  ]);
}

function unusedBlock(entries: [string, ApiOperation][], used: Set<string>, i18n: I18n): string {
  const body = entries
    .filter(([id]) => !used.has(id))
    .map(([id, op]) => indent(endpointNode(id, op, UNUSED_FILL)))
    .join("\n");
  if (body === "") return "";
  return `unused: "${i18n.unusedTitle}" {\n${body}\n  style.stroke-dash: 4\n  style.fill: "#fafafa"\n}`;
}

function legendEntry(id: string, label: string, shape: string, styles: string[]): string[] {
  return [`  ${id}: "${label}"`, `  ${id}.shape: ${shape}`, ...styles.map((s) => `  ${id}.${s}`)];
}

function legendD2(model: Model, used: Set<string>, i18n: I18n): string {
  const entries = Object.entries(model.api ?? {});
  const usedKinds = new Set(entries.filter(([id]) => used.has(id)).map(([, op]) => op.kind));
  const items: string[][] = [];
  if (usedKinds.has("api")) items.push(legendEntry("legend_api", "API", "parallelogram", [`style.fill: "${API_FILL.api}"`]));
  if (usedKinds.has("html")) items.push(legendEntry("legend_html", "HTML UI", "parallelogram", [`style.fill: "${API_FILL.html}"`]));
  if (entries.some(([id]) => !used.has(id))) {
    items.push(legendEntry("legend_unused", i18n.unusedLegend, "parallelogram", [`style.fill: "${UNUSED_FILL}"`]));
  }
  if (Object.values(model.screens ?? {}).some((s) => (s.references ?? []).length > 0)) {
    items.push(legendEntry("legend_ref", i18n.referenceLegend, "parallelogram", ['style.stroke-dash: 4', 'style.stroke: "#999999"']));
  }
  if (Object.keys(model.entities).length > 0) {
    items.push(legendEntry("legend_entity", i18n.entityLegend, "cylinder", []));
  }
  if (items.length === 0) return "";
  return [`legend: "${i18n.legend}" {`, ...items.flat(), "}"].join("\n");
}

export function apiMapD2(model: Model, i18n: I18n = DEFAULT_I18N): string {
  const entries = Object.entries(model.api ?? {});
  const used = usedEndpointIds(model);
  const screens = Object.entries(model.screens ?? {})
    .map(([id, screen]) => `${id}: "${id}\\n${screen.name}"`)
    .join("\n");
  const usedEndpoints = entries
    .filter(([id]) => used.has(id))
    .map(([id, op]) => endpointNode(id, op, endpointFill(op)))
    .join("\n");
  const entities = Object.entries(model.entities)
    .map(([id]) => `${id}: "${id}\\n(${i18n.entity})"\n${id}.shape: cylinder`)
    .join("\n");
  const screenCalls = [
    ...new Set(
      (model.navigation ?? [])
        .filter((n) => n.call !== undefined)
        .map((n) => `${n.from} -> ${n.call}: "${n.on.replace(/"/g, "'")}"`),
    ),
  ];
  const referenceEdges = Object.entries(model.screens ?? {}).flatMap(([id, screen]) =>
    (screen.references ?? []).map((ref) => `${id} -> ${ref}: "${i18n.reference}" {\n  style.stroke-dash: 4\n  style.stroke: "#999999"\n}`),
  );
  const entityCalls = entries
    .filter(([, op]) => op.entity !== undefined)
    .map(([id, op]) => {
      const source = used.has(id) ? id : `unused.${id}`;
      return `${source} -> ${op.entity}`;
    });
  const loads = Object.entries(model.screens ?? {})
    .filter(([, screen]) => screen.onLoad !== undefined)
    .map(([id, screen]) => `${id} -> ${screen.onLoad}: "${i18n.initial}"`);
  return [
    "direction: right",
    "",
    screens,
    "",
    usedEndpoints,
    "",
    entities,
    "",
    unusedBlock(entries, used, i18n),
    "",
    legendD2(model, used, i18n),
    "",
    [...screenCalls, ...referenceEdges, ...entityCalls, ...loads].join("\n"),
    "",
  ].join("\n");
}

export type RenderKind = "logical" | "physical" | "flow" | "nav" | "api" | "graph" | "static";

export function renderD2(
  model: Model,
  kind: RenderKind,
  options: { typeMap?: Record<string, string>; i18n?: Partial<I18n> } = {},
): string {
  const typeMap = options.typeMap ?? {};
  const i18n: I18n = { ...DEFAULT_I18N, ...options.i18n };
  switch (kind) {
    case "logical":
      return logicalD2(model);
    case "physical":
      return physicalD2(model, typeMap);
    case "flow":
      return flowD2(model);
    case "nav":
      return navD2(model);
    case "api":
      return apiMapD2(model, i18n);
    case "graph":
      return "";
    case "static":
      return "";
  }
}
