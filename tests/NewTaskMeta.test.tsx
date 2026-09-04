import { renderToString } from "hono/jsx/dom/server";
import { describe, expect, it } from "vite-plus/test";
import { NewTaskMeta } from "../src/components/NewTaskMeta";

describe("NewTaskMeta", () => {
  it("renders status radio choices with the selected status", () => {
    const html = renderToString(<NewTaskMeta state={{ status: "done", area: 3, from: "matrix" }} />);

    expect(html).toContain('<details data-popover-close="status">');
    expect(html).toContain("Apply status to this task");
    expect(html).toContain('name="status" value="done" checked');
    expect(html).toContain('name="area" value="3" checked');
    expect(html).toContain('<button type="button" class="status-choice" data-popover-cancel="true">');
  });

  it("renders area radio choices with the selected area", () => {
    const html = renderToString(<NewTaskMeta state={{ status: "do", area: 2, from: "tasks" }} />);

    expect(html).toContain('<details data-popover-close="area">');
    expect(html).toContain("Apply area to this task");
    expect(html).toContain('name="status" value="do" checked');
    expect(html).toContain('name="area" value="2" checked');
  });
});
