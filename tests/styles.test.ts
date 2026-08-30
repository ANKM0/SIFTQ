import { describe, expect, it } from "vite-plus/test";
import { STYLES_CSS } from "../src/styles";

describe("styles", () => {
  it("defines the wireframe shell, matrix axes, rows, and popover", () => {
    expect(STYLES_CSS).toContain(".topbar");
    expect(STYLES_CSS).toContain(".matrix-axis");
    expect(STYLES_CSS).toContain(".task-row");
    expect(STYLES_CSS).toContain(".popover");
  });

  it("uses the full quadrant body as the Matrix drop target", () => {
    expect(STYLES_CSS).toMatch(/\.area--quadrant \.matrix-cards\s*\{\s*flex: 1;/);
  });
});
