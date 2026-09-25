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

  it("uses a single-column Matrix on narrow screens", () => {
    const matrix = STYLES_CSS.match(/(?:^|\n)\.matrix\s*\{[^}]*\}/);
    expect(matrix?.[0]).toContain("grid-template-columns: minmax(0, 1fr);");
    expect(STYLES_CSS).toContain("@media (width >= 40rem)");
    expect(STYLES_CSS).toContain("grid-template-columns: repeat(2, minmax(0, 1fr));");
  });

  it("uses a dark border for Matrix cards against the light Matrix frame", () => {
    const taskCard = STYLES_CSS.match(/(?:^|\n)\.task-card\s*\{[^}]*\}/);
    const matrixAxis = STYLES_CSS.match(/(?:^|\n)\.matrix-axis\s*\{[^}]*\}/);
    expect(taskCard?.[0]).toContain("border-color: #24292f;");
    expect(matrixAxis?.[0]).toContain("border: 1px solid #d0d7de;");
  });

  it("does not override the cursor on draggable Matrix cards", () => {
    expect(STYLES_CSS).not.toContain('.task-card[draggable="true"]');
    const taskCardRules = STYLES_CSS.match(/(?:^|\n)\.task-card[^{]*{[^}]*}/g) ?? [];
    expect(taskCardRules.some((rule) => /cursor:\s*(grab|grabbing)/.test(rule))).toBe(false);
  });

  it("places the four quadrant areas in their Matrix grid cells", () => {
    const q1 = STYLES_CSS.match(/(?:^|\n)\.area--q1\s*\{[^}]*\}/);
    expect(q1?.[0]).toContain("grid-column: 1;");
    expect(q1?.[0]).toContain("grid-row: 1;");

    const q2 = STYLES_CSS.match(/(?:^|\n)\.area--q2\s*\{[^}]*\}/);
    expect(q2?.[0]).toContain("grid-column: 1;");
    expect(q2?.[0]).toContain("grid-row: 2;");

    const q3 = STYLES_CSS.match(/(?:^|\n)\.area--q3\s*\{[^}]*\}/);
    expect(q3?.[0]).toContain("grid-column: 1;");
    expect(q3?.[0]).toContain("grid-row: 3;");

    const q4 = STYLES_CSS.match(/(?:^|\n)\.area--q4\s*\{[^}]*\}/);
    expect(q4?.[0]).toContain("grid-column: 1;");
    expect(q4?.[0]).toContain("grid-row: 4;");
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

});

describe("styles regression guards", () => {
  it("keeps Matrix rows symmetric so the horizontal axis line lands on the quadrant boundary", () => {
    expect(STYLES_CSS).toContain("grid-template-rows: repeat(2, minmax(0, 1fr));");
  });

  it("keeps mobile quadrant cards in the page flow and desktop cards scrollable", () => {
    expect(STYLES_CSS).toContain("overflow-y: visible;");
    expect(STYLES_CSS).toContain("overflow-y: auto;");
  });

  it("lets quadrant content shrink so equal rows are not stretched by card overflow", () => {
    const quadrant = STYLES_CSS.match(/(?:^|\n)\.area--quadrant\s*\{[^}]*\}/);
    expect(quadrant?.[0]).toContain("min-height: 0;");
  });

  it("stacks the Status and Area side panel on narrow screens", () => {
    expect(STYLES_CSS).toMatch(
      /\.detail-grid\s*\{\s*display: grid;\s*gap: 16px;\s*grid-template-columns: minmax\(0, 1fr\);/,
    );
    expect(STYLES_CSS).toContain("@media (width >= 48rem)");
    expect(STYLES_CSS).toContain("grid-template-columns: minmax(0, 1fr) 250px;");
    expect(STYLES_CSS).toContain(".page--new .detail-grid");
    expect(STYLES_CSS).toContain(".page--detail .detail-grid");
  });

  it("keeps popovers within a narrow viewport", () => {
    expect(STYLES_CSS).toContain("width: min(360px, calc(100vw - 32px));");
    expect(STYLES_CSS).toContain("@media (width < 40rem)");
  });
});

describe("Idea card description divider", () => {
  it("draws a top border above the description but not on empty cards", () => {
    const description = STYLES_CSS.match(/(?:^|\n)\.idea-card__description\s*\{[^}]*\}/);
    expect(description?.[0]).toContain("border-top: 1px solid #8b949e;");

    const empty = STYLES_CSS.match(/(?:^|\n)\.idea-card__description--empty\s*\{[^}]*\}/);
    expect(empty?.[0]).toContain("border-top: 0;");
  });
});

describe("Matrix drag feedback styles", () => {
  it("floats the Matrix drag ghost without capturing pointer events", () => {
    const ghost = STYLES_CSS.match(/(?:^|\n)\.matrix-drag-ghost\s*\{[^}]*\}/);
    expect(ghost?.[0]).toContain("position: fixed;");
    expect(ghost?.[0]).toContain("pointer-events: none;");
    expect(ghost?.[0]).toMatch(/z-index: \d+;/);

    const placeholder = STYLES_CSS.match(/(?:^|\n)\.matrix-drag-placeholder\s*\{[^}]*\}/);
    expect(placeholder?.[0]).toContain("pointer-events: none;");
  });
});
