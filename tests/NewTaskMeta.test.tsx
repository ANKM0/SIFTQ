import { describe, expect, it } from "vite-plus/test";
import { NewTaskMeta } from "../src/components/NewTaskMeta";

describe("NewTaskMeta", () => {
  it("renders the selected status menu while preserving the area", () => {
    const html = String(<NewTaskMeta state={{ status: "done", area: 3, openMenu: "status" }} />);

    expect(html).toContain("Apply status to this task");
    expect(html).toContain("status=done&amp;area=3");
    expect(html).toContain("done");
    expect(html).toContain("skip");
  });

  it("renders the selected area menu while preserving the status", () => {
    const html = String(<NewTaskMeta state={{ status: "do", area: 2, openMenu: "area" }} />);

    expect(html).toContain("Apply area to this task");
    expect(html).toContain("status=do&amp;area=2");
    expect(html).toContain("1");
    expect(html).toContain("4");
  });
});
