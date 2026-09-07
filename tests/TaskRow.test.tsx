import { renderToString } from "hono/jsx/dom/server";
import { describe, expect, it } from "vite-plus/test";
import { TaskRow } from "../src/components/TaskRow";
import { taskFixture } from "./helpers/task-fixture";

describe("TaskRow", () => {
  it("renders issue number, title, area, and status", () => {
    const html = renderToString(<TaskRow task={taskFixture({ id: "task-1" })} issueNumber={1} />);
    expect(html).toContain("#1");
    expect(html).toContain("seed task");
    expect(html).toContain("1");
    expect(html).toContain("do");
  });

  it("marks working tasks with a badge and working class", () => {
    const html = renderToString(<TaskRow task={taskFixture({ working: true })} issueNumber={1} />);
    expect(html).toContain('class="task-row task-row--working"');
    expect(html).toContain('class="working-badge">working</span>');
  });
});
