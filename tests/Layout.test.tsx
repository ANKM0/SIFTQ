import { renderToString } from "hono/jsx/dom/server";
import { describe, expect, it } from "vite-plus/test";
import { Layout } from "../src/components/Layout";

describe("Layout", () => {
  it("renders an html document", () => {
    const html = renderToString(<Layout active="matrix"><span>content</span></Layout>);
    expect(html).toContain("<html");
    expect(html).toContain('id="page"');
    expect(html).toContain('src="/htmx-conflict.js"');
    expect(html).toContain('src="/popover-dismiss.js"');
  });
});
