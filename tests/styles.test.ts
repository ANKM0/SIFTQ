import { describe, expect, it } from "vite-plus/test";
import { STYLES_CSS } from "../src/styles";

describe("styles", () => {
  it("defines the application shell, matrix axes, rows, and popover", () => {
    expect(STYLES_CSS).toContain(".topbar");
    expect(STYLES_CSS).toContain(".matrix-axis");
    expect(STYLES_CSS).toContain(".task-row");
    expect(STYLES_CSS).toContain(".popover");
  });

  it("uses the full quadrant body as the Matrix drop target", () => {
    expect(STYLES_CSS).toMatch(/\.area--quadrant \.matrix-cards\s*\{\s*flex: 1;/);
  });

  it("keeps Matrix rows symmetric so the horizontal axis line lands on the quadrant boundary", () => {
    const matrixAxis = STYLES_CSS.match(/(?:^|\n)\.matrix-axis\s*\{[^}]*\}/);
    expect(matrixAxis?.[0]).toContain("grid-template-rows: repeat(2, minmax(0, 1fr));");
  });

  it("keeps overflowing quadrant cards scrollable inside each quadrant", () => {
    const matrixCards = STYLES_CSS.match(/\.area--quadrant \.matrix-cards\s*\{[^}]*\}/);
    expect(matrixCards?.[0]).toContain("overflow-y: auto;");
  });

  it("lets quadrant content shrink so equal rows are not stretched by card overflow", () => {
    const quadrant = STYLES_CSS.match(/(?:^|\n)\.area--quadrant\s*\{[^}]*\}/);
    expect(quadrant?.[0]).toContain("min-height: 0;");
  });

  it("uses a 250px Status and Area side panel on new and detail pages", () => {
    expect(STYLES_CSS).toMatch(
      /\.detail-grid\s*\{\s*display: grid;\s*gap: 16px;\s*grid-template-columns: minmax\(0, 1fr\) 250px;/,
    );
    expect(STYLES_CSS).toContain(".page--new .detail-grid");
    expect(STYLES_CSS).toContain(".page--detail .detail-grid");
  });
});
