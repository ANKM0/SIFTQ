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
});
