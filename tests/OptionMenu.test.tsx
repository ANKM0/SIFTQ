import { renderToString } from "hono/jsx/dom/server";
import { describe, expect, it } from "vite-plus/test";
import { OptionMenu } from "../src/components/OptionMenu";
import { taskFixture } from "./helpers/task-fixture";

describe("OptionMenu", () => {
  it("renders all status choices in a popover", () => {
    const html = renderToString(<OptionMenu task={taskFixture({ id: "task-1" })} open="status" />);
    expect(html).toContain("Apply status to this task");
    expect(html).toContain("do");
    expect(html).toContain("done");
    expect(html).toContain("skip");
  });

  it("renders all area choices in a popover", () => {
    const html = renderToString(<OptionMenu task={taskFixture({ id: "task-1" })} open="area" />);
    expect(html).toContain("Apply area to this task");
    expect(html).toContain("1");
    expect(html).toContain("2");
    expect(html).toContain("3");
    expect(html).toContain("4");
  });
});
