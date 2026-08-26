import { describe, expect, it } from "vite-plus/test";
import { TaskCard } from "../src/components/TaskCard";
import { taskFixture } from "./helpers/task-fixture";

describe("TaskCard", () => {
  it("renders the task title and data attributes", () => {
    const html = String(<TaskCard task={taskFixture({ id: "task-1" })} />);
    expect(html).toContain('data-task-id="task-1"');
    expect(html).toContain("seed task");
  });
});
