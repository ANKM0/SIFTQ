import { describe, expect, it } from "vite-plus/test";
import { Layout } from "../src/components/Layout";

describe("Layout", () => {
  it("renders an html document", () => {
    const html = String(<Layout active="matrix"><span>content</span></Layout>);
    expect(html).toContain("<html");
    expect(html).toContain('id="page"');
    expect(html).toContain("htmx:beforeSwap");
    expect(html).toContain("xhr.status !== 409");
  });
});
