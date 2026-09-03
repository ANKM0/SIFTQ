import { describe, expect, it } from "vite-plus/test";
import { NewTaskMeta } from "../src/components/NewTaskMeta";

describe("NewTaskMeta", () => {
  it("renders status radio choices with the selected status", () => {
    const html = String(<NewTaskMeta state={{ status: "done", area: 3, from: "matrix" }} />);

    expect(html).toContain("Apply status to this task");
    expect(html).toContain('name="status" value="done" checked');
    expect(html).toContain('name="area" value="3" checked');
  });

  it("renders area radio choices with the selected area", () => {
    const html = String(<NewTaskMeta state={{ status: "do", area: 2, from: "tasks" }} />);

    expect(html).toContain("Apply area to this task");
    expect(html).toContain('name="status" value="do" checked');
    expect(html).toContain('name="area" value="2" checked');
  });
});
