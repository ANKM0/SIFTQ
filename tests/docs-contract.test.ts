import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT_DIR = fileURLToPath(new URL("..", import.meta.url));

const DOC_FILES: readonly string[] = ["README.md", "taskfile/core.yml"];

const REQUIRED_README_TERMS: readonly string[] = [
  "Hono",
  "HTMX",
  "SortableJS",
  "Cloudflare Worker",
  "D1",
];

const FORBIDDEN_SPA_TERMS: readonly string[] = [
  "React",
  "SPA",
  "Vite",
  "dnd-kit",
  "browser storage",
];

function readDoc(relativePath: string): string {
  return readFileSync(join(ROOT_DIR, relativePath), "utf8");
}

function hasTerm(content: string, term: string): boolean {
  return new RegExp(`\\b${term}\\b`).test(content);
}

describe("documentation architecture contract", () => {
  it("describes the README app as Hono JSX on a Cloudflare Worker with HTMX, SortableJS, and D1", () => {
    const readme = readDoc("README.md");
    const missing = REQUIRED_README_TERMS.filter(
      (term) => !readme.includes(term),
    );
    expect(
      missing,
      `README.md must describe the current architecture but is missing: ${missing.join(", ")}`,
    ).toEqual([]);
    expect(readme).toContain("task frontend:dev");
    expect(readme.toLowerCase()).toContain("wrangler");
  });

  it("does not describe the app as a React SPA in the README or Taskfile", () => {
    const violations: string[] = [];
    for (const file of DOC_FILES) {
      const content = readDoc(file);
      for (const term of FORBIDDEN_SPA_TERMS) {
        if (hasTerm(content, term)) {
          violations.push(`${file}: contains "${term}"`);
        }
      }
    }
    expect(violations).toEqual([]);
  });
});
