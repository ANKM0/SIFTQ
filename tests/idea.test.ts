import { describe, expect, it } from "vite-plus/test";
import { sortIdeas } from "../src/idea";

describe("Ideas", () => {
  it("sorts independent ideas by order", () => {
    const ideas = [
      { title: "second", description: "", order: 2, pinned: false },
      { title: "first", description: "", order: 1, pinned: false },
    ];

    expect(sortIdeas(ideas).map((idea) => idea.title)).toEqual(["first", "second"]);
  });
});
