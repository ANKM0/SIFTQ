#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, resolve } from "node:path";
import { runAdapters } from "./adapters.ts";
import { check } from "./check.ts";
import { loadConfig, resolveConfigPath, type ResolvedConfig, type View } from "./config.ts";
import { checkAuto, readAuto, runExtractors, writeAuto } from "./extract.ts";
import { graphData, type GraphDecoration } from "./graph.ts";
import { loadPresentation, mergeModel, writeModel } from "./merge.ts";
import type { Model } from "./model.ts";
import { patchSvgDimensions } from "./patch-svg.ts";
import { renderD2 } from "./render.ts";
import { serveDir } from "./serve.ts";
import { validate } from "./validate.ts";

function isMain(): boolean {
  const entry = process.argv[1];
  if (entry === undefined) return false;
  try {
    return fileURLToPath(import.meta.url) === resolve(entry);
  } catch {
    return false;
  }
}

function flag(args: string[], name: string): string | undefined {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : undefined;
}

function hasFlag(args: string[], name: string): boolean {
  return args.includes(name);
}

function readJson(path: string): unknown {
  return JSON.parse(readFileSync(path, "utf8"));
}

// Build the model from the code-derived auto graph + the manual presentation.
function syncModel(config: ResolvedConfig, checkOnly: boolean): void {
  const configured = config.extractors.length > 0 || existsSync(resolveConfigPath(config, config.presentation)) || existsSync(resolveConfigPath(config, config.auto));
  if (!configured) return;

  let auto = readAuto(config) ?? {};
  if (config.extractors.length > 0) {
    auto = runExtractors(config);
    if (checkOnly) checkAuto(config, auto);
    else writeAuto(config, auto);
  }

  const model = mergeModel(auto, loadPresentation(config));
  if (checkOnly) {
    const path = resolveConfigPath(config, config.model);
    const current = existsSync(path) ? readJson(path) : undefined;
    if (JSON.stringify(current) !== JSON.stringify(model)) {
      console.error(`${config.model} is stale; run the sync command`);
      process.exit(1);
    }
    return;
  }
  console.log(`wrote ${writeModel(config, model)}`);
}

function writeViewer(config: ResolvedConfig): string {
  const views: Record<string, { label: string; src: string; type: string }> = {};
  for (const view of config.views) {
    const type = view.kind === "graph" ? "graph" : "image";
    views[view.key] = { label: view.label, src: `${view.key}.${type === "graph" ? "json" : "svg"}`, type };
  }
  const template = readFileSync(new URL("./viewer/template.html", import.meta.url), "utf8");
  const html = template
    .replace("__TITLE__", config.title)
    .replace("/*__VIEWS__*/", JSON.stringify(views, null, 2))
    .replace("/*__DEFAULT__*/", JSON.stringify(config.views[0]?.key ?? ""));
  const outDir = resolveConfigPath(config, config.outDir);
  mkdirSync(outDir, { recursive: true });
  const file = join(outDir, "viewer.html");
  writeFileSync(file, html);
  return file;
}

async function generate(config: ResolvedConfig): Promise<void> {
  const model = readJson(resolveConfigPath(config, config.model)) as Model;
  const schema = readJson(resolveConfigPath(config, config.schema)) as object;

  const schemaErrors = validate(model, schema);
  if (schemaErrors.length > 0) {
    console.error("model violates schema:");
    for (const error of schemaErrors) console.error(`  - ${error}`);
    process.exit(1);
  }

  const adapterResult = await runAdapters(config, model);
  const { errors, warnings } = check(model, { api: config.api, extra: adapterResult });
  for (const warning of warnings) console.warn(`warn: ${warning}`);
  if (errors.length > 0) {
    console.error("cross-check violations:");
    for (const error of errors) console.error(`  - ${error}`);
    process.exit(1);
  }

  const outDir = resolveConfigPath(config, config.outDir);
  mkdirSync(outDir, { recursive: true });
  const presentation = loadPresentation(config);
  const decoration = (presentation as { graph?: GraphDecoration }).graph;
  for (const view of config.views) {
    if (view.kind === "graph") {
      writeFileSync(join(outDir, `${view.key}.json`), `${JSON.stringify(graphData(model, decoration), null, 2)}\n`);
      console.log(`wrote ${view.key}.json`);
      continue;
    }
    if (view.kind === "static") continue;
    const d2 = renderD2(model, view.kind, { typeMap: config.typeMap, i18n: config.i18n });
    writeFileSync(join(outDir, `${view.key}.d2`), d2);
    console.log(`wrote ${view.key}.d2`);
  }
  if (config.views.some((view) => view.kind === "graph")) {
    copyFileSync(new URL("./viewer/vis-network.min.js", import.meta.url), join(outDir, "vis-network.min.js"));
  }
  console.log(`wrote ${writeViewer(config)}`);
}

function compileD2(config: ResolvedConfig, view: View, input: string): void {
  const outDir = resolveConfigPath(config, config.outDir);
  const output = join(outDir, `${view.key}.svg`);
  const args = ["--pad", "10"];
  if (view.layout !== undefined) args.push(`--layout=${view.layout}`);
  args.push(input, output);
  const result = spawnSync("d2", args, { stdio: "inherit" });
  if (result.error) {
    console.error(`failed to run d2 (is it installed?): ${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) process.exit(result.status ?? 1);
  patchSvgDimensions(output);
}

function compile(config: ResolvedConfig): void {
  const outDir = resolveConfigPath(config, config.outDir);
  for (const view of config.views) {
    if (view.kind === "graph") continue;
    if (view.kind === "static") {
      if (view.source !== undefined) compileD2(config, view, resolveConfigPath(config, view.source));
      continue;
    }
    compileD2(config, view, join(outDir, `${view.key}.d2`));
  }
}

function patch(config: ResolvedConfig): void {
  const outDir = resolveConfigPath(config, config.outDir);
  for (const view of config.views) {
    const output = join(outDir, `${view.key}.svg`);
    try {
      patchSvgDimensions(output);
    } catch {
      // svg not generated yet; skip
    }
  }
}

function copyDir(src: string, dest: string): void {
  mkdirSync(dest, { recursive: true });
  for (const entry of readdirSync(src, { withFileTypes: true })) {
    const from = join(src, entry.name);
    const to = join(dest, entry.name);
    if (entry.isDirectory()) copyDir(from, to);
    else copyFileSync(from, to);
  }
}

function requireConfig(args: string[]): ResolvedConfig {
  const configPath = flag(args, "--config");
  if (configPath === undefined) {
    console.error("--config <path> is required");
    process.exit(2);
  }
  return loadConfig(configPath);
}

async function main(argv: string[]): Promise<void> {
  const [command, ...args] = argv;
  switch (command) {
    case "generate":
      syncModel(requireConfig(args), false);
      await generate(requireConfig(args));
      return;
    case "sync":
      syncModel(requireConfig(args), hasFlag(args, "--check"));
      return;
    case "build": {
      const config = requireConfig(args);
      syncModel(config, hasFlag(args, "--check"));
      await generate(config);
      compile(config);
      patch(config);
      return;
    }
    case "patch":
      patch(requireConfig(args));
      return;
    case "serve": {
      const config = requireConfig(args);
      const port = Number(flag(args, "--port") ?? "8765");
      const served = await serveDir(resolveConfigPath(config, config.outDir), port);
      console.log(`serving ${served.url}`);
      return;
    }
    case "init": {
      const target = resolve(flag(args, "--dir") ?? ".");
      copyDir(fileURLToPath(new URL("../template/", import.meta.url)), target);
      console.log(`copied template to ${target}`);
      return;
    }
    default:
      console.error("usage: blueprint <generate|sync|build|patch|serve|init> [--config <path>] [--check]");
      process.exit(2);
  }
}

if (isMain()) {
  main(process.argv.slice(2)).catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  });
}
