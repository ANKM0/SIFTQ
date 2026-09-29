import { renderToString } from "hono/jsx/dom/server";
import { describe, expect, it } from "vite-plus/test";
import { TaskCard } from "../src/components/TaskCard";
import { taskFixture } from "./helpers/task-fixture";

describe("TaskCard", () => {
  it("renders the task title and data attributes", () => {
    const html = renderToString(<TaskCard task={taskFixture({ id: "task-1" })} />);
    expect(html).toContain('data-task-id="task-1"');
    expect(html).toContain('draggable="false"');
    expect(html).toContain("seed task");
  });

  it("does not render the task status badge", () => {
    const html = renderToString(<TaskCard task={taskFixture({ status: "do" })} />);
    expect(html).not.toContain("status--do");
    expect(html).not.toContain(">do</span>");
  });

  it("marks working tasks with a badge and working class", () => {
    const html = renderToString(<TaskCard task={taskFixture({ working: true })} />);
    expect(html).toContain('class="task-card task-card--working"');
    expect(html).toContain('class="working-badge">working</span>');
  });

  it("renders the description text in the clamped description element", () => {
    const html = renderToString(<TaskCard task={taskFixture({ description: "first line\nsecond line" })} />);
    expect(html).toContain('class="task-card-description"');
    expect(html).toContain("first line");
    expect(html).not.toContain("/api/images/");
  });

  it("omits the description element when the description is empty", () => {
    const html = renderToString(<TaskCard task={taskFixture({ description: "" })} />);
    expect(html).not.toContain("task-card-description");
  });

  it("renders only the first image and the remaining image count", () => {
    const html = renderToString(
      <TaskCard task={taskFixture({ description: "/api/images/first /api/images/second /api/images/third" })} />,
    );
    expect(html).toContain('class="task-card-image description-image"');
    expect(html).toContain('src="/api/images/first"');
    expect(html).not.toContain('src="/api/images/second"');
    expect(html).toContain("+2");
  });

  it("does not render an image count when only one image is present", () => {
    const html = renderToString(<TaskCard task={taskFixture({ description: "/api/images/only" })} />);
    expect(html).toContain('src="/api/images/only"');
    expect(html).not.toContain("task-card-image-count");
  });

  it("does not render images for a text-only description", () => {
    const html = renderToString(<TaskCard task={taskFixture({ description: "just text" })} />);
    expect(html).not.toContain("task-card-image");
  });
});
