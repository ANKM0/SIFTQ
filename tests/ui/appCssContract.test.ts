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
      /\.task-detail-form__actions\s*\{[\s\S]*?justify-content:\s*space-between;[\s\S]*?align-items:\s*flex-end;[\s\S]*?gap:\s*16px;[\s\S]*?margin-top:\s*20px;[\s\S]*?\}/
    );
    expect(appCss).toMatch(
      /\.task-detail-form__back-link\s*\{[\s\S]*?align-self:\s*flex-end;[\s\S]*?min-width:\s*0;[\s\S]*?\}/
    );
    expect(appCss).toMatch(
      /\.task-detail-form__action-group\s*\{[\s\S]*?column-gap:\s*20px;[\s\S]*?row-gap:\s*12px;[\s\S]*?\}/
    );
    expect(appCss).toMatch(
      /@media \(max-width: 840px\)\s*\{[\s\S]*?\.task-detail-form__actions\s*\{[\s\S]*?width:\s*100%;[\s\S]*?justify-content:\s*stretch;[\s\S]*?\}[\s\S]*?\.task-detail-form__action-group\s*\{[\s\S]*?grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\);[\s\S]*?width:\s*100%;[\s\S]*?\}[\s\S]*?\.task-detail-form__action-group \.tasks-page__button\s*\{[\s\S]*?width:\s*100%;[\s\S]*?\}/
    );
    expect(appCss).toMatch(
      /@media \(max-width: 720px\)\s*\{[\s\S]*?\.task-detail-form__action-group\s*\{[\s\S]*?grid-auto-flow:\s*row;[\s\S]*?width:\s*100%;[\s\S]*?\}[\s\S]*?\.task-detail-form__action-group \.tasks-page__button\s*\{[\s\S]*?width:\s*100%;[\s\S]*?\}/
    );
  });

  it("allows task buttons to wrap instead of overflowing", () => {
    expect(appCss).toMatch(
      /\.tasks-page__button\s*\{[\s\S]*?max-width:\s*100%;[\s\S]*?line-height:\s*1\.3;[\s\S]*?white-space:\s*normal;[\s\S]*?overflow-wrap:\s*anywhere;[\s\S]*?\}/
    );
  });

  it("keeps the task detail form in two columns until narrow widths, then collapses cleanly", () => {
    expect(appCss).toMatch(
      /\.task-detail-form__grid\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0,\s*1fr\)\s*minmax\(220px,\s*280px\);[\s\S]*?gap:\s*16px;[\s\S]*?\}/
    );
    expect(appCss).toMatch(
      /@media \(max-width: 720px\)\s*\{[\s\S]*?\.task-detail-form__grid\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0,\s*1fr\);[\s\S]*?\}/
    );
  });
});
