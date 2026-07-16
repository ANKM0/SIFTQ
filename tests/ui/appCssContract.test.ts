import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const currentDir = dirname(fileURLToPath(import.meta.url));
const appCss = readFileSync(resolve(currentDir, "../../src/ui/App.css"), "utf8");

describe("App CSS contract", () => {
  it("preserves the mobile single-column matrix workspace layout", () => {
    expect(appCss).toContain("@media (max-width: 900px)");
    expect(appCss).toMatch(
      /@media \(max-width: 900px\)\s*\{[\s\S]*?\.matrix-workspace\s*\{\s*grid-template-columns:\s*1fr;\s*\}/
    );
  });

  it("keeps terminal drop areas usable on mobile widths", () => {
    expect(appCss).toMatch(
      /@media \(max-width: 900px\)\s*\{[\s\S]*?\.status-drop-area\s*\{\s*min-height:\s*96px;\s*\}/
    );
  });

  it("keeps task detail delete and save actions separated on desktop and mobile", () => {
    expect(appCss).toMatch(
      /\.task-detail-form__action-group\s*\{[\s\S]*?column-gap:\s*20px;[\s\S]*?row-gap:\s*12px;[\s\S]*?\}/
    );
    expect(appCss).toMatch(
      /@media \(max-width: 720px\)\s*\{[\s\S]*?\.task-detail-form__action-group\s*\{[\s\S]*?grid-auto-flow:\s*row;[\s\S]*?width:\s*100%;[\s\S]*?\}[\s\S]*?\.task-detail-form__action-group \.tasks-page__button\s*\{[\s\S]*?width:\s*100%;[\s\S]*?\}/
    );
  });
});
