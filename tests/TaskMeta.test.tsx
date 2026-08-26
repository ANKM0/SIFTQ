import { describe, expect, it } from "vite-plus/test";
import { TaskMeta } from "../src/components/TaskMeta";
import { taskFixture } from "./helpers/task-fixture";

describe("TaskMeta", () => {
  it("renders status and area", () => {
    const html = String(<TaskMeta task={taskFixture({ status: "do", area: 1 })} />);
    expect(html).toContain("do");
    expect(html).toContain("1");
  });
});
