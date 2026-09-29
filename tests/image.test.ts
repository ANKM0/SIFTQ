import { describe, expect, it } from "vite-plus/test";
import { IMAGE_MAX_BYTES, isImageContentType } from "../src/image";

describe("isImageContentType", () => {
  it.each(["image/png", "image/webp", "image/jpeg"])("accepts %s", (contentType) => {
    expect(isImageContentType(contentType)).toBe(true);
  });

  it.each(["image/gif", "image/svg+xml", "text/plain", ""])("rejects %s", (contentType) => {
    expect(isImageContentType(contentType)).toBe(false);
  });

  it("allows up to one mebibyte", () => {
    expect(IMAGE_MAX_BYTES).toBe(1024 * 1024);
  });
});
