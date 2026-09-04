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

  it("keeps the Matrix quadrants in a 2-column equal grid", () => {
    const matrix = STYLES_CSS.match(/(?:^|\n)\.matrix\s*\{[^}]*\}/);
    expect(matrix?.[0]).toContain("grid-template-columns: repeat(2, minmax(0, 1fr));");
  });

  it("places the four quadrant areas in their Matrix grid cells", () => {
    const q1 = STYLES_CSS.match(/(?:^|\n)\.area--q1\s*\{[^}]*\}/);
    expect(q1?.[0]).toContain("grid-column: 1;");
    expect(q1?.[0]).toContain("grid-row: 1;");

    const q2 = STYLES_CSS.match(/(?:^|\n)\.area--q2\s*\{[^}]*\}/);
    expect(q2?.[0]).toContain("grid-column: 2;");
    expect(q2?.[0]).toContain("grid-row: 1;");

    const q3 = STYLES_CSS.match(/(?:^|\n)\.area--q3\s*\{[^}]*\}/);
    expect(q3?.[0]).toContain("grid-column: 1;");
    expect(q3?.[0]).toContain("grid-row: 2;");

    const q4 = STYLES_CSS.match(/(?:^|\n)\.area--q4\s*\{[^}]*\}/);
    expect(q4?.[0]).toContain("grid-column: 2;");
    expect(q4?.[0]).toContain("grid-row: 2;");
  });

  it("keeps quadrant areas as flex columns layered above the crosshair", () => {
    const quadrant = STYLES_CSS.match(/(?:^|\n)\.area--quadrant\s*\{[^}]*\}/);
    expect(quadrant?.[0]).toContain("display: flex;");
    expect(quadrant?.[0]).toContain("flex-direction: column;");
    expect(quadrant?.[0]).toContain("position: relative;");
    expect(quadrant?.[0]).toContain("z-index: 1;");
  });

  it("keeps the horizontal axis line centered on the quadrant boundary", () => {
    const horizontal = STYLES_CSS.match(/(?:^|\n)\.axis-line--horizontal\s*\{[^}]*\}/);
    expect(horizontal?.[0]).toContain("inset: 50% 20px auto;");
    expect(horizontal?.[0]).toContain("transform: translateY(-50%);");
  });

  it("keeps the vertical axis line centered on the quadrant boundary", () => {
    const vertical = STYLES_CSS.match(/(?:^|\n)\.axis-line--vertical\s*\{[^}]*\}/);
    expect(vertical?.[0]).toContain("inset: 72px auto 72px 50%;");
    expect(vertical?.[0]).toContain("transform: translateX(-50%);");
  });

  it("allocates an explicit grid row for the matrix sort controls", () => {
    const page = STYLES_CSS.match(/(?:^|\n)\.page--matrix\s*\{[^}]*\}/);
    expect(page?.[0]).toContain("grid-template-rows: auto auto auto minmax(0, 1fr);");
    const sort = STYLES_CSS.match(/(?:^|\n)\.matrix-sort\s*\{[^}]*\}/);
    expect(sort?.[0]).toContain("display: flex;");
    expect(sort?.[0]).toContain("min-height: 34px;");
  });
});

describe("styles regression guards", () => {
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
