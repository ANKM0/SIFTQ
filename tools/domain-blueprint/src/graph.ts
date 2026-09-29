import type { Model } from "./model.ts";

// Generic interactive graph data derived from the model. The optional presentation.graph
// section only decorates it (areas, labels, colors); it does not change the relationships.

export type GraphNode = { id: string; label: string; group: string; shape?: string; title?: string; x?: number; y?: number };
export type GraphEdge = { id: string; from: string; to: string; color: string; dashes?: boolean; title?: string };
export type GraphDecoration = {
  areas?: Record<string, string>;
  areaLabels?: Record<string, string>;
  areaColors?: Record<string, string>;
  labels?: Record<string, string>;
};
export type GraphData = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  legend: { areaColors: Record<string, string>; edge: { write: string; read: string; both: string } };
};

const WRITE_COLOR = "#2f9e44";
const READ_COLOR = "#1c7ed6";
const BOTH_COLOR = "#7048e8";
const CLIENT_COLOR = "#adb5bd";
const DEFAULT_AREA_COLOR = "#e8f0ff";

export function graphData(model: Model, decoration: GraphDecoration = {}): GraphData {
  const api = Object.entries(model.api ?? {}).filter(([, op]) => op.kind === "api");
  const screens = model.screens ?? {};
  const screenCalls = model.screenCalls ?? [];
  const navigation = model.navigation ?? [];
  const calledApis = new Set(screenCalls.map((call) => call.api));

  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  const seen = new Set<string>();
  const addNode = (node: GraphNode): void => {
    if (seen.has(node.id)) return;
    seen.add(node.id);
    nodes.push(node);
  };

  for (const [key, op] of api) {
    addNode({ id: `api:${key}`, label: `${op.method} ${op.path}`, group: "api", shape: "box", title: `${op.method} ${op.path}` });
  }
  for (const name of Object.keys(model.entities)) {
    addNode({ id: `entity:${name}`, label: name, group: "entity", shape: "database" });
  }

  const screenIds = new Set<string>([...Object.keys(screens), ...screenCalls.map((call) => call.screen)]);
  for (const id of screenIds) {
    addNode({ id: `screen:${id}`, label: screens[id]?.name ?? id, group: "client", shape: "box" });
  }
  const serverOnly = api.some(([key]) => !calledApis.has(key));
  if (serverOnly) addNode({ id: "server", label: "server (non-screen)", group: "client", shape: "box" });

  const addEdge = (edge: GraphEdge): void => {
    if (edges.some((existing) => existing.id === edge.id)) return;
    edges.push(edge);
  };

  if (screenCalls.length > 0) {
    for (const call of screenCalls) addEdge({ id: `c:${call.screen}->${call.api}`, from: `screen:${call.screen}`, to: `api:${call.api}`, color: CLIENT_COLOR, title: call.trigger });
  } else {
    for (const nav of navigation) if (nav.call) addEdge({ id: `c:${nav.from}->${nav.call}`, from: `screen:${nav.from}`, to: `api:${nav.call}`, color: CLIENT_COLOR, title: nav.on });
    for (const [id, screen] of Object.entries(screens)) if (screen.onLoad) addEdge({ id: `c:${id}->${screen.onLoad}`, from: `screen:${id}`, to: `api:${screen.onLoad}`, color: CLIENT_COLOR });
  }
  for (const [key] of api) if (serverOnly && !calledApis.has(key)) addEdge({ id: `c:server->${key}`, from: "server", to: `api:${key}`, color: CLIENT_COLOR });

  for (const [key, op] of api) {
    const writes = new Set([...(op.entities ?? []), ...(op.entity !== undefined ? [op.entity] : [])]);
    const reads = new Set(op.references ?? []);
    for (const entity of new Set([...writes, ...reads])) {
      if (!(entity in model.entities)) continue;
      const write = writes.has(entity);
      const read = reads.has(entity);
      addEdge({
        id: `e:${key}->${entity}`,
        from: `api:${key}`,
        to: `entity:${entity}`,
        color: write && read ? BOTH_COLOR : write ? WRITE_COLOR : READ_COLOR,
        dashes: !write && read,
        title: write && read ? "write+read" : write ? "write" : "read",
      });
    }
  }

  applyLayout(nodes, decoration);

  const areaColors: Record<string, string> = {};
  for (const node of nodes) {
    const area = decoration.areas?.[node.id];
    if (area) areaColors[area] = decoration.areaColors?.[area] ?? DEFAULT_AREA_COLOR;
  }
  for (const node of nodes) {
    const area = decoration.areas?.[node.id];
    node.group = area ? `area_${area}` : node.group;
    const label = decoration.labels?.[node.id];
    if (label) node.label = label;
  }

  return { nodes, edges, legend: { areaColors, edge: { write: WRITE_COLOR, read: READ_COLOR, both: BOTH_COLOR } } };
}

function applyLayout(nodes: GraphNode[], decoration: GraphDecoration): void {
  const X_STEP = 170;
  const API_COLS = 12;
  const API_ROW_STEP = 90;
  const API_TOP = 220;
  const clients = nodes.filter((node) => node.id === "server" || node.id.startsWith("screen:"));
  const apis = nodes.filter((node) => node.id.startsWith("api:"));
  const entities = nodes.filter((node) => node.id.startsWith("entity:"));
  clients.forEach((node, index) => {
    node.x = (index - (clients.length - 1) / 2) * X_STEP;
    node.y = 0;
  });
  apis.forEach((node, index) => {
    node.x = ((index % API_COLS) - (API_COLS - 1) / 2) * X_STEP;
    node.y = API_TOP + Math.floor(index / API_COLS) * API_ROW_STEP;
  });
  const rows = Math.ceil(apis.length / API_COLS);
  entities.forEach((node, index) => {
    node.x = (index - (entities.length - 1) / 2) * X_STEP;
    node.y = API_TOP + rows * API_ROW_STEP + 140;
  });
}
