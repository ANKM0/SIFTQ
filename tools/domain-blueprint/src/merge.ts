import { existsSync, readFileSync, writeFileSync } from "node:fs";
import type { ResolvedConfig } from "./config.ts";
import { resolveConfigPath } from "./config.ts";
import type { PartialModel } from "./extract.ts";
import type { Model } from "./model.ts";

// Merge the code-derived auto graph with the manual presentation.
// Dict sections are merged key-by-key (presentation wins); list sections support
// add/remove overrides keyed by a stable identity; flows stay manual.

const DICT_KEYS = ["domains", "entities", "screens", "api"] as const;
const LIST_KEYS = ["relations", "navigation", "screenCalls"] as const;

type Presentation = PartialModel & { overrides?: Record<string, { add?: unknown[]; remove?: unknown[] }> };

function identity(key: string, item: unknown): string {
  const record = item as Record<string, unknown>;
  if (key === "relations" || key === "navigation") return `${record.from}->${record.to}:${record.on ?? ""}`;
  if (key === "screenCalls") return `${record.screen}|${record.trigger}|${record.api}`;
  return JSON.stringify(item);
}

export function mergeModel(auto: PartialModel, presentation: Presentation): Model {
  const out = {} as Model;
  for (const key of DICT_KEYS) {
    out[key] = { ...((auto[key] ?? {}) as object), ...((presentation[key] ?? {}) as object) } as never;
  }
  for (const key of LIST_KEYS) {
    const autoList = (auto[key] ?? []) as unknown[];
    const manualList = (presentation[key] ?? []) as unknown[];
    const base = autoList.length > 0 ? autoList : manualList;
    const override = presentation.overrides?.[key] ?? {};
    const removed = new Set((override.remove ?? []).map((item) => identity(key, item)));
    const merged = base.filter((item) => !removed.has(identity(key, item)));
    merged.push(...(override.add ?? []));
    out[key] = merged as never;
  }
  out.flows = (presentation.flows ?? auto.flows ?? {}) as Model["flows"];
  out.persistence = (auto.persistence ?? presentation.persistence) as Model["persistence"];
  return out;
}

export function loadPresentation(config: ResolvedConfig): Presentation {
  const path = resolveConfigPath(config, config.presentation);
  if (!existsSync(path)) return {};
  return JSON.parse(readFileSync(path, "utf8")) as Presentation;
}

export function writeModel(config: ResolvedConfig, model: Model): string {
  const path = resolveConfigPath(config, config.model);
  writeFileSync(path, `${JSON.stringify(model, null, 2)}\n`);
  return path;
}
