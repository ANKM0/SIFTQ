import { describe, expect, it } from "vite-plus/test";
import { BRAND_NAME } from "../src/brand";

describe("BRAND_NAME", () => {
  it("is a non-empty service-independent display name", () => {
    expect(BRAND_NAME.trim().length).toBeGreaterThan(0);
    expect(BRAND_NAME.toLowerCase()).not.toContain("siftq");
  });
});
