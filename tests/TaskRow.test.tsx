import { describe, expect, it } from "vite-plus/test";
import { TaskRow } from "../src/components/TaskRow";
import { taskFixture } from "./helpers/task-fixture";

describe("TaskRow", () => {
  it("renders task id, title, area, and status", () => {
    const html = String(<TaskRow task={taskFixture({ id: "task-1" })} />);
    expect(html).toContain("task-1");
    expect(html).toContain("seed task");
    expect(html).toContain("Area 1");
    expect(html).toContain("do");
  });
});
