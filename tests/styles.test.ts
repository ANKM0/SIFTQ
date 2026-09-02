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

  it("uses a 250px Status and Area side panel on new and detail pages", () => {
    expect(STYLES_CSS).toMatch(
      /\.detail-grid\s*\{\s*display: grid;\s*gap: 16px;\s*grid-template-columns: minmax\(0, 1fr\) 250px;/,
    );
    expect(STYLES_CSS).toContain(".page--new .detail-grid");
    expect(STYLES_CSS).toContain(".page--detail .detail-grid");
  });
});
