import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { test as base } from "@playwright/test";
import type { BrowserContext, Page } from "@playwright/test";

const HTMX_URL = "https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js";

const cachePath = fileURLToPath(new URL("../../tmp/e2e-htmx.min.js", import.meta.url));

let htmxSource: Promise<string> | undefined;

async function loadHtmx(): Promise<string> {
  if (existsSync(cachePath)) return readFileSync(cachePath, "utf8");
  for (let attempt = 0; attempt < 5; attempt += 1) {
    try {
      const response = await fetch(HTMX_URL);
      if (response.ok) {
        const source = await response.text();
        mkdirSync(dirname(cachePath), { recursive: true });
        writeFileSync(cachePath, source);
        return source;
      }
    } catch {
      continue;
    }
  }
  throw new Error(`Unable to fetch ${HTMX_URL} for the E2E htmx fixture`);
}

export async function installHtmxRoute(target: Page | BrowserContext): Promise<void> {
  htmxSource ??= loadHtmx();
  const source = await htmxSource;
  await target.route(HTMX_URL, (route) => route.fulfill({ contentType: "application/javascript", body: source }));
}

export const e2eBaseUrl = `http://127.0.0.1:${process.env["E2E_PORT"] ?? "4173"}`;

export const test = base.extend({
  context: async ({ context }, use) => {
    await installHtmxRoute(context);
    await use(context);
  },
});

export { expect } from "@playwright/test";
