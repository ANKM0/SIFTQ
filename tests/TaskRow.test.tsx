import { renderToString } from "hono/jsx/dom/server";
import { describe, expect, it } from "vite-plus/test";
import { TaskRow } from "../src/components/TaskRow";
import { taskFixture } from "./helpers/task-fixture";

describe("TaskRow", () => {
  it("renders title, area, and status without an issue number", () => {
    const html = renderToString(<TaskRow task={taskFixture({ id: "task-1" })} />);
    expect(html).not.toContain("issue-number");
    expect(html).not.toContain("#1");
    expect(html).toContain("seed task");
    expect(html).toContain("1");
    expect(html).toContain("do");
    expect(html).toContain('data-task-id="task-1"');
    expect(html).toContain('data-version="1"');
  });

  it("marks working tasks with a badge and working class", () => {
    const html = renderToString(<TaskRow task={taskFixture({ working: true })} />);
    expect(html).toContain('class="task-row task-row--working"');
    expect(html).toContain('class="working-badge">working</span>');
  });
});
