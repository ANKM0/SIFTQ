import { describe, expect, it } from "vite-plus/test";
import { BRAND_NAME, FAVICON_HREF } from "../src/brand";

describe("BRAND_NAME", () => {
  it("is a non-empty service-independent display name", () => {
    expect(BRAND_NAME.trim().length).toBeGreaterThan(0);
    expect(BRAND_NAME.toLowerCase()).not.toContain("siftq");
  });
});

describe("FAVICON_HREF", () => {
  it("encodes a four-quadrant SVG as an inline data URI", () => {
    const prefix = "data:image/svg+xml,";
    expect(FAVICON_HREF.startsWith(prefix)).toBe(true);

    const svg = decodeURIComponent(FAVICON_HREF.slice(prefix.length));
    expect(svg.startsWith("<svg")).toBe(true);
    expect(svg.endsWith("</svg>")).toBe(true);
    expect(svg.match(/<rect\b/g)).toHaveLength(5);
  });
});
