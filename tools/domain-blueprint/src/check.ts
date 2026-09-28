import type { ApiError, Model, Step, Transition } from "./model.ts";

export type CheckOptions = {
  api?: { pathPrefix?: string; crudVerbs?: string[] };
  extra?: { errors?: string[]; warnings?: string[] };
};

const DEFAULT_PATH_PREFIX = "/api/";
const DEFAULT_CRUD_VERBS = ["create", "update", "delete", "remove", "get", "list", "fetch", "save", "edit", "new"];
const API_SUCCESS_BY_METHOD: Record<string, number[]> = {
  GET: [200],
  POST: [200, 201],
  PATCH: [200],
  DELETE: [204],
};
const HTML_SUCCESS_BY_METHOD: Record<string, number[]> = {
  GET: [200],
  POST: [200, 201, 302, 303],
};

function checkAttributeDomains(model: Model): string[] {
  const errors: string[] = [];
  for (const [name, entity] of Object.entries(model.entities)) {
    for (const [attr, a] of Object.entries(entity.attributes)) {
      if (!(a.domain in model.domains)) errors.push(`entities.${name}.attributes.${attr}.domain is not in domains: ${a.domain}`);
    }
  }
  return errors;
}

function transitionErrors(name: string, t: Transition, model: Model, domain: string): string[] {
  const values = model.domains[domain]?.values ?? [];
  const errors: string[] = [];
  for (const endpoint of [t.from].flat()) {
    if (!values.includes(endpoint)) errors.push(`entities.${name}.transitions "${t.on}" from=${endpoint} is not in domains.${domain}.values`);
  }
  if (!values.includes(t.to)) errors.push(`entities.${name}.transitions "${t.on}" to=${t.to} is not in domains.${domain}.values`);
  return errors;
}

function checkTransitions(model: Model): string[] {
  const errors: string[] = [];
  for (const [name, entity] of Object.entries(model.entities)) {
    for (const t of entity.transitions ?? []) {
      if (t.domain === undefined) {
        errors.push(`entities.${name}.transitions "${t.on}" has no domain`);
        continue;
      }
      errors.push(...transitionErrors(name, t, model, t.domain));
    }
  }
  return errors;
}

function checkRelations(model: Model): string[] {
  const errors: string[] = [];
  for (const r of model.relations ?? []) {
    if (!(r.from in model.entities)) errors.push(`relations.from is not in entities: ${r.from}`);
    if (!(r.to in model.entities)) errors.push(`relations.to is not in entities: ${r.to}`);
  }
  return errors;
}

function checkFlowStep(model: Model, flowId: string, step: Step): string[] {
  if (step.entity === undefined || step.changes === undefined) return [];
  if (!(step.entity in model.entities)) return [`flows.${flowId} step "${step.name}" entity is not in entities: ${step.entity}`];
  const attrs = model.entities[step.entity]?.attributes ?? {};
  return Object.keys(step.changes)
    .filter((key) => !(key in attrs))
    .map((key) => `flows.${flowId} step "${step.name}" changes.${key} is not in entities.${step.entity}.attributes`);
}

function checkFlows(model: Model): string[] {
  return Object.entries(model.flows ?? {}).flatMap(([flowId, flow]) =>
    flow.steps.flatMap((step) => checkFlowStep(model, flowId, step)),
  );
}

function checkScreens(model: Model): string[] {
  return Object.entries(model.screens ?? {}).flatMap(([id, screen]) => {
    const errors = screen.entities
      .filter((ref) => !(ref in model.entities))
      .map((ref) => `screens.${id}.entities is not in entities: ${ref}`);
    if (screen.onLoad !== undefined) {
      const op = model.api?.[screen.onLoad];
      if (op === undefined) errors.push(`screens.${id}.onLoad is not in api: ${screen.onLoad}`);
      else if (op.kind !== "html" || op.method !== "GET") errors.push(`screens.${id}.onLoad must be an html GET: ${screen.onLoad}`);
    }
    for (const ref of screen.references ?? []) {
      if (model.api?.[ref] === undefined) errors.push(`screens.${id}.references is not in api: ${ref}`);
    }
    return errors;
  });
}

function checkNavigation(model: Model): string[] {
  const screenKeys = new Set(Object.keys(model.screens ?? {}));
  const errors: string[] = [];
  for (const nav of model.navigation ?? []) {
    if (!screenKeys.has(nav.from)) errors.push(`navigation.from is not in screens: ${nav.from}`);
    if (!screenKeys.has(nav.to)) errors.push(`navigation.to is not in screens: ${nav.to}`);
  }
  return errors;
}

function checkApiPath(where: string, kind: string, path: string, pathPrefix: string, crudVerbs: Set<string>): string[] {
  const errors: string[] = [];
  if (kind === "api" && !path.startsWith(pathPrefix)) errors.push(`${where}.path must start with ${pathPrefix}: ${path}`);
  if (kind === "html" && path.startsWith(pathPrefix)) errors.push(`${where}.path is an HTML UI endpoint, not ${pathPrefix}: ${path}`);
  if (path.length > 1 && path.endsWith("/")) errors.push(`${where}.path must not end with a slash: ${path}`);
  if (path !== path.toLowerCase()) errors.push(`${where}.path must be lowercase: ${path}`);
  for (const segment of path.split("/")) {
    if (segment === "" || /^\{[a-z]+\}$/.test(segment)) continue;
    if (!/^[a-z][a-z0-9-]*$/.test(segment)) errors.push(`${where}.path segment must be a lowercase noun: ${segment}`);
    else if (kind === "api" && crudVerbs.has(segment)) errors.push(`${where}.path must not contain a CRUD verb: ${segment}`);
  }
  return errors;
}

function checkApiSuccess(where: string, kind: string, method: string, success: number): string[] {
  const allowed = (kind === "html" ? HTML_SUCCESS_BY_METHOD : API_SUCCESS_BY_METHOD)[method];
  if (allowed === undefined) return [`${where}.method must be one of ${Object.keys(API_SUCCESS_BY_METHOD).join("/")}: ${method}`];
  if (!allowed.includes(success)) return [`${where}.success for ${method} must be ${allowed.join("/")}: ${success}`];
  return [];
}

function checkApiErrors(where: string, errors: ApiError[]): string[] {
  return errors
    .filter((e) => e.status < 400 || e.status > 599)
    .map((e) => `${where}.errors.status must be 4xx/5xx: ${e.status}`);
}

function checkApi(model: Model, pathPrefix: string, crudVerbs: Set<string>): string[] {
  return Object.entries(model.api ?? {}).flatMap(([id, op]) => {
    const where = `api.${id}`;
    const unknownEntity =
      op.entity !== undefined && !(op.entity in model.entities) ? [`${where}.entity is not in entities: ${op.entity}`] : [];
    return [
      ...checkApiPath(where, op.kind, op.path, pathPrefix, crudVerbs),
      ...checkApiSuccess(where, op.kind, op.method, op.success),
      ...unknownEntity,
      ...checkApiErrors(where, op.errors ?? []),
    ];
  });
}

function checkNavigationCalls(model: Model): string[] {
  const known = new Set(Object.keys(model.api ?? {}));
  return (model.navigation ?? [])
    .filter((n) => n.call !== undefined && !known.has(n.call))
    .map((n) => `navigation ${n.from} -> ${n.to} call is not in api: ${n.call}`);
}

function checkUnreferencedEntities(model: Model): string[] {
  const referenced = new Set(Object.values(model.screens ?? {}).flatMap((s) => s.entities));
  return Object.keys(model.entities)
    .filter((key) => !referenced.has(key))
    .map((key) => `entity "${key}" is not referenced by any screen`);
}

export function check(model: Model, options: CheckOptions = {}): { errors: string[]; warnings: string[] } {
  const pathPrefix = options.api?.pathPrefix ?? DEFAULT_PATH_PREFIX;
  const crudVerbs = new Set(options.api?.crudVerbs ?? DEFAULT_CRUD_VERBS);
  const errors = [
    ...checkAttributeDomains(model),
    ...checkTransitions(model),
    ...checkRelations(model),
    ...checkFlows(model),
    ...checkScreens(model),
    ...checkNavigation(model),
    ...checkApi(model, pathPrefix, crudVerbs),
    ...checkNavigationCalls(model),
    ...(options.extra?.errors ?? []),
  ];
  return {
    errors,
    warnings: [...checkUnreferencedEntities(model), ...(options.extra?.warnings ?? [])],
  };
}
