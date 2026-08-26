import { describe, expect, it } from "vite-plus/test";
import { STYLES_CSS } from "../src/styles";

describe("styles", () => {
  it("defines the four UI states and title wrapping", () => {
    expect(STYLES_CSS).toContain(".page--empty");
    expect(STYLES_CSS).toContain(".page--loading");
    expect(STYLES_CSS).toContain(".page--error");
    expect(STYLES_CSS).toContain("overflow-wrap: anywhere");
  });
});
