import { describe, expect, it } from "vite-plus/test";
import { splitDescription } from "../src/description";

describe("splitDescription", () => {
  it("splits http and https URLs into link segments", () => {
    expect(splitDescription("Read https://example.com/docs and http://localhost:8787."))
      .toEqual([
        { text: "Read " },
        { text: "https://example.com/docs", href: "https://example.com/docs" },
        { text: " and " },
        { text: "http://localhost:8787", href: "http://localhost:8787" },
        { text: "." },
      ]);
  });

  it("does not link non-http schemes", () => {
    expect(splitDescription("javascript:alert(1) www.example.com")).toEqual([
      { text: "javascript:alert(1) www.example.com" },
    ]);
  });

  it("splits image tokens into image segments", () => {
    expect(splitDescription("before /api/images/abc-123 after")).toEqual([
      { text: "before " },
      { text: "/api/images/abc-123", src: "/api/images/abc-123" },
      { text: " after" },
    ]);
  });

  it("keeps surrounding punctuation outside an image token", () => {
    expect(splitDescription("/api/images/abc-123.")).toEqual([
      { text: "/api/images/abc-123", src: "/api/images/abc-123" },
      { text: "." },
    ]);
  });

  it("does not treat an image token inside a URL as an image", () => {
    expect(splitDescription("https://example.com/api/images/abc")).toEqual([
      { text: "https://example.com/api/images/abc", href: "https://example.com/api/images/abc" },
    ]);
  });
});
