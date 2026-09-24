import { describe, expect, it } from "vite-plus/test";
import { sortIdeas } from "../src/idea";

describe("Ideas", () => {
  it("sorts independent ideas by order", () => {
    const ideas = [
      { title: "second", description: "", order: 2 },
      { title: "first", description: "", order: 1 },
    ];

    expect(sortIdeas(ideas).map((idea) => idea.title)).toEqual(["first", "second"]);
  });
});
