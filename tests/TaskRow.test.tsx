import { describe, expect, it } from "vite-plus/test";
import { TaskRow } from "../src/components/TaskRow";
import { taskFixture } from "./helpers/task-fixture";

describe("TaskRow", () => {
  it("renders issue number, title, area, and status", () => {
    const html = String(<TaskRow task={taskFixture({ id: "task-1" })} issueNumber={1} />);
    expect(html).toContain("#1");
    expect(html).toContain("seed task");
    expect(html).toContain("1");
    expect(html).toContain("do");
  });
});
