import { pathToFileURL } from "node:url";
import type { ResolvedConfig } from "./config.ts";
import { resolveConfigPath } from "./config.ts";
import type { Model } from "./model.ts";

export type AdapterContext = { model: Model; config: ResolvedConfig };
export type AdapterResult = { errors?: string[]; warnings?: string[] };
export type Adapter = (ctx: AdapterContext) => AdapterResult | Promise<AdapterResult>;

export async function runAdapters(config: ResolvedConfig, model: Model): Promise<AdapterResult> {
  const errors: string[] = [];
  const warnings: string[] = [];
  for (const entry of config.adapters) {
    const path = resolveConfigPath(config, entry);
    const mod = (await import(pathToFileURL(path).href)) as { adapter?: Adapter; default?: Adapter };
    const adapter = mod.adapter ?? mod.default;
    if (typeof adapter !== "function") {
      errors.push(`adapter ${entry} does not export an adapter function`);
      continue;
    }
    const result = await adapter({ model, config });
    errors.push(...(result.errors ?? []));
    warnings.push(...(result.warnings ?? []));
  }
  return { errors, warnings };
}
