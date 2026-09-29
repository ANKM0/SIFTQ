import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("../../", import.meta.url));

const ENTITIES = new Set(["tasks", "ideas"]);
const HTTP_VERBS = new Set(["GET", "POST", "PATCH", "DELETE", "PUT"]);

const HTML_PAGE_IDS: Record<string, string> = {
  "/login": "html_login_page",
  "/matrix": "html_matrix_page",
  "/ideas": "html_ideas_page",
  "/ideas/:id": "html_ideas_detail",
  "/tasks": "html_tasks_page",
  "/tasks/new": "html_new_task_page",
  "/tasks/:id": "html_task_page",
};

const PAGE_ENTITY: Record<string, string> = {
  "/matrix": "tasks",
  "/ideas": "ideas",
  "/ideas/:id": "ideas",
  "/tasks": "tasks",
  "/tasks/:id": "tasks",
};

const SCREEN_BY_FILE: Record<string, string[]> = {
  "matrix-scripts.ts": ["P01"],
  "task-list-scripts.ts": ["P02"],
  "task-form-scripts.ts": ["P03", "P04"],
  "idea-scripts.ts": ["P08"],
};

export type ApiError = { status: number; code?: string };
export type ApiOperation = {
  kind: "api" | "html";
  method: string;
  path: string;
  operation: string;
  entity?: string;
  success: number;
  errors?: ApiError[];
};
export type ScreenCall = { screen: string; trigger: "GET" | "POST"; view: string; gateway: string; api: string };
export type PartialModel = { api?: Record<string, ApiOperation>; screenCalls?: ScreenCall[] };
export type Route = { method: string; path: string };
export type ClientCall = { file: string; method: string; path: string };

export function parseRoutes(source: string): Route[] {
  const routes: Route[] = [];
  const re = /app\.(get|post|patch|delete|put)\("([^"]+)"/g;
  let match = re.exec(source);
  while (match !== null) {
    const method = match[1];
    const path = match[2];
    if (method !== undefined && path !== undefined) routes.push({ method: method.toUpperCase(), path });
    match = re.exec(source);
  }
  return routes;
}

function segments(path: string): string[] {
  return path.split("/").filter((segment) => segment !== "");
}

function isParam(segment: string): boolean {
  return segment.startsWith(":") || /^\{[^}]+\}$/.test(segment);
}

function paramName(segment: string): string {
  return segment.replace(/^:/, "").replace(/[{}]/g, "");
}

function modelPath(path: string): string {
  return path.replace(/:(\w+)/g, "{$1}");
}

function build(id: string, operation: string, method: string, path: string, success: number, entity?: string): { id: string; operation: ApiOperation } {
  const op: ApiOperation = { kind: path.startsWith("/api/") ? "api" : "html", method, path: modelPath(path), operation, success };
  if (entity !== undefined) op.entity = entity;
  return { id, operation: op };
}

const API_ACTIONS: Record<string, { suffix: string; operation: string }> = {
  "GET:empty": { suffix: "list", operation: "list" },
  "GET:param": { suffix: "get", operation: "get" },
  "POST:empty": { suffix: "create", operation: "create" },
  "PATCH:param": { suffix: "patch", operation: "patch" },
  "DELETE:param": { suffix: "delete", operation: "delete" },
};

function tailShape(tail: string[]): string {
  if (tail.length === 0) return "empty";
  if (tail.length === 1 && tail[0] !== undefined && isParam(tail[0])) return "param";
  return "other";
}

function apiAction(method: string, resource: string, tail: string[], tailNames: string[]): { id: string; operation: string } {
  const entry = API_ACTIONS[`${method}:${tailShape(tail)}`];
  if (entry !== undefined) return { id: `${resource}_${entry.suffix}`, operation: entry.operation };
  const operation = method === "DELETE" ? `${tailNames.join("-")}-delete` : tailNames.join("-");
  return { id: `${resource}_${operation.replace(/-/g, "_")}`, operation };
}

function apiSuccess(method: string, operation: string): number {
  if (method === "GET") return 200;
  if (method === "DELETE") return 204;
  if (method === "POST" && operation === "create") return 201;
  return 200;
}

function apiRoute(method: string, path: string): { id: string; operation: ApiOperation } | null {
  const segs = segments(path).slice(1);
  const resource = segs[0];
  if (resource === undefined) return null;
  const tail = segs.slice(1);
  const tailNames = tail.map((segment) => (isParam(segment) ? paramName(segment) : segment));
  const action = apiAction(method, resource, tail, tailNames);
  const entity = ENTITIES.has(resource) ? resource : undefined;
  return build(action.id, action.operation, method, path, apiSuccess(method, action.operation), entity);
}

function htmlRoute(method: string, path: string): { id: string; operation: ApiOperation } | null {
  if (method === "GET") {
    const id = HTML_PAGE_IDS[path];
    if (id === undefined) return null;
    return build(id, "load", method, path, 200, PAGE_ENTITY[path]);
  }
  if (method !== "POST") return null;
  const segs = segments(path);
  const resource = segs[0];
  if (resource === undefined) return null;
  const tail = segs.slice(1);
  if (tail.length === 0) {
    const entity = ENTITIES.has(resource) ? resource : undefined;
    if (entity === undefined) return build(`html_${resource}`, resource, method, path, 302);
    return build(`html_${resource}_create`, "create", method, path, 201, entity);
  }
  const first = tail[0];
  if (tail.length === 1 && first !== undefined && isParam(first)) {
    return build(`html_${resource}_update`, "update", method, path, 200, resource);
  }
  const action = tail[1];
  if (tail.length === 2 && first !== undefined && isParam(first) && action !== undefined) {
    return build(`html_${resource}_${action}`, action, method, path, 200, resource);
  }
  return null;
}

export function routeToApi(route: Route): { id: string; operation: ApiOperation } | null {
  return route.path.startsWith("/api/") ? apiRoute(route.method, route.path) : htmlRoute(route.method, route.path);
}

function matchApiPaths(line: string): string[] {
  const paths: string[] = [];
  const re = /"(\/api\/[^"]*)"/g;
  let match = re.exec(line);
  while (match !== null) {
    const raw = match[1];
    if (raw !== undefined) {
      const after = line.slice(match.index + match[0].length);
      const concatenated = /^\s*\+/.test(after);
      let cleaned = raw;
      while (cleaned.endsWith("\\")) cleaned = cleaned.slice(0, -1);
      paths.push(concatenated && cleaned.endsWith("/") ? `${cleaned}{id}` : cleaned);
    }
    match = re.exec(line);
  }
  return paths;
}

function matchMethods(window: string): string[] {
  const methods: string[] = [];
  const re = /"([A-Z]+)\\*"/g;
  let match = re.exec(window);
  while (match !== null) {
    const verb = match[1];
    if (verb !== undefined && HTTP_VERBS.has(verb)) methods.push(verb);
    match = re.exec(window);
  }
  return methods;
}

function pairCalls(paths: string[], methods: string[]): { method: string; path: string }[] {
  const fallback = methods[0];
  if (fallback === undefined) return [];
  if (paths.length !== methods.length) return paths.map((path) => ({ method: fallback, path }));
  return paths.flatMap((path, index) => {
    const method = methods[index];
    return method === undefined ? [] : [{ method, path }];
  });
}

function extractLineCalls(line: string, lines: string[], index: number): { method: string; path: string }[] {
  if (!line.includes("/api/")) return [];
  const paths = matchApiPaths(line);
  if (paths.length === 0) return [];
  return pairCalls(paths, matchMethods(lines.slice(index, index + 2).join("\n")));
}

export function extractClientCalls(source: string): { method: string; path: string }[] {
  const lines = source.split("\n");
  return lines.flatMap((line, index) => extractLineCalls(line, lines, index));
}

export function buildAuto(routes: Route[], calls: ClientCall[], meta: Record<string, { errors?: ApiError[] }>): PartialModel {
  const api: Record<string, ApiOperation> = {};
  const lookup = new Map<string, string>();
  for (const route of routes) {
    if (route.path === "/" || route.path.includes("/menu")) continue;
    const mapped = routeToApi(route);
    if (mapped === null) continue;
    const errors = meta[mapped.id]?.errors;
    if (errors !== undefined) mapped.operation.errors = errors;
    api[mapped.id] = mapped.operation;
    lookup.set(`${mapped.operation.method} ${mapped.operation.path}`, mapped.id);
  }
  const screenCalls: ScreenCall[] = [];
  const seen = new Set<string>();
  for (const call of calls) {
    const id = lookup.get(`${call.method} ${call.path}`);
    if (id === undefined) continue;
    for (const screen of SCREEN_BY_FILE[call.file] ?? []) {
      const key = `${screen}|POST|${id}`;
      if (seen.has(key)) continue;
      seen.add(key);
      screenCalls.push({ screen, trigger: "POST", view: `screen:${screen}`, gateway: call.file, api: id });
    }
  }
  return { api, screenCalls };
}

function readSourceFiles(dir: string, extensions: string[]): { name: string; source: string }[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .sort()
    .filter((name) => extensions.some((extension) => name.endsWith(extension)))
    .map((name) => ({ name, source: readFileSync(join(dir, name), "utf8") }));
}

function readApiMeta(): Record<string, { errors?: ApiError[] }> {
  const metaPath = join(ROOT, "scripts/domain-model/api-meta.json");
  if (!existsSync(metaPath)) return {};
  const parsed: Record<string, { errors?: ApiError[] }> = JSON.parse(readFileSync(metaPath, "utf8"));
  return parsed;
}

export function buildAutoFromProject(): PartialModel {
  const routes = readSourceFiles(join(ROOT, "src/routes"), [".ts", ".tsx"]).flatMap((file) => parseRoutes(file.source));
  const calls = readSourceFiles(join(ROOT, "src/client"), [".ts"]).flatMap((file) =>
    extractClientCalls(file.source).map((call) => ({ file: file.name, method: call.method, path: call.path })),
  );
  return buildAuto(routes, calls, readApiMeta());
}

function isMain(): boolean {
  const entry = process.argv[1];
  if (entry === undefined) return false;
  try {
    return fileURLToPath(import.meta.url) === resolve(entry);
  } catch {
    return false;
  }
}

if (isMain()) {
  process.stdout.write(`${JSON.stringify(buildAutoFromProject(), null, 2)}\n`);
}
