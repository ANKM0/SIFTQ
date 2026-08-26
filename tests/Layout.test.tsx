import { describe, expect, it } from "vite-plus/test";
import { Layout } from "../src/components/Layout";

describe("Layout", () => {
  it("renders an html document", () => {
    const html = String(<Layout>content</Layout>);
    expect(html).toContain("<html");
    expect(html).toContain('id="page"');
  });
});
