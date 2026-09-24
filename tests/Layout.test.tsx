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
    expect(html).toContain('src="/task-form-shortcut.js"');
  });

  it("orders the primary nav as Ideas, Matrix, Tasks", () => {
    for (const active of ["ideas", "matrix", "tasks"] as const) {
      const html = renderToString(<Layout active={active}><span>content</span></Layout>);
      const nav = html.slice(html.indexOf("<nav"), html.indexOf("</nav>"));
      const ideas = nav.indexOf('href="/ideas"');
      const matrix = nav.indexOf('href="/matrix"');
      const tasks = nav.indexOf('href="/tasks"');
      expect(ideas).toBeGreaterThanOrEqual(0);
      expect(matrix).toBeGreaterThanOrEqual(0);
      expect(tasks).toBeGreaterThanOrEqual(0);
      expect(ideas).toBeLessThan(matrix);
      expect(matrix).toBeLessThan(tasks);
      expect(nav).toContain(`href="/${active}"`);
    }
  });
});
