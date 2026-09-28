import { readFileSync } from "node:fs";
import { dirname, isAbsolute, resolve } from "node:path";
import type { I18n, RenderKind } from "./render.ts";

export type View = { key: string; label: string; kind: RenderKind; layout?: "elk" | "dagre" };

export type BlueprintConfig = {
  title: string;
  model: string;
  schema: string;
  outDir: string;
  views: View[];
  typeMap: Record<string, string>;
  api: { pathPrefix?: string; crudVerbs?: string[] };
  i18n: Partial<I18n>;
  adapters: string[];
};

export type ResolvedConfig = BlueprintConfig & { configDir: string; configPath: string };

const DEFAULT_VIEWS: View[] = [
  { key: "logical", label: "Logical ER", kind: "logical" },
  { key: "physical", label: "Physical ER", kind: "physical", layout: "dagre" },
  { key: "flow", label: "Flow", kind: "flow" },
  { key: "nav", label: "Screens", kind: "nav" },
  { key: "api", label: "API", kind: "api", layout: "elk" },
];

export function loadConfig(configPath: string): ResolvedConfig {
  const absolute = resolve(configPath);
  const raw = JSON.parse(readFileSync(absolute, "utf8")) as Partial<BlueprintConfig>;
  return {
    title: raw.title ?? "domain blueprint",
    model: raw.model ?? "domain-model.json",
    schema: raw.schema ?? "domain-model.schema.json",
    outDir: raw.outDir ?? "generated",
    views: raw.views ?? DEFAULT_VIEWS,
    typeMap: raw.typeMap ?? {},
    api: raw.api ?? {},
    i18n: raw.i18n ?? {},
    adapters: raw.adapters ?? [],
    configDir: dirname(absolute),
    configPath: absolute,
  };
}

export function resolveConfigPath(config: ResolvedConfig, path: string): string {
  return isAbsolute(path) ? path : resolve(config.configDir, path);
}
