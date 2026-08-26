import { describe, expect, it } from "vite-plus/test";
import { OptionMenu } from "../src/components/OptionMenu";

describe("OptionMenu", () => {
  it("renders all values", () => {
    const html = String(
      <OptionMenu
        title="Change status"
        values={["do", "done", "skip"]}
        postPath="/tasks/task-1/status"
        valueKey="status"
        cancelPath="/tasks/task-1"
        version={1}
      />,
    );
    expect(html).toContain("do");
    expect(html).toContain("done");
    expect(html).toContain("skip");
  });
});
