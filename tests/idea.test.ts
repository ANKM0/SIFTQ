import { describe, expect, it } from "vite-plus/test";
import {
  applyIdeaPatch,
  nextIdeaOrder,
  parseIdeaPatch,
  sortIdeas,
  type Idea,
} from "../src/idea";

function ideaFixture(overrides: Partial<Idea> = {}): Idea {
  return {
    id: "idea-1",
    owner_id: "local",
    title: "idea",
    description: "",
    order: 1,
    pinned: false,
    ...overrides,
  };
}

describe("Ideas", () => {
  it("sorts independent ideas by order", () => {
    const ideas = [
      { id: "second", owner_id: "local", title: "second", description: "", order: 2, pinned: false },
      { id: "first", owner_id: "local", title: "first", description: "", order: 1, pinned: false },
    ];

    expect(sortIdeas(ideas).map((idea) => idea.title)).toEqual(["first", "second"]);
  });

  it("numbers the next order within the same pinned group", () => {
    const ideas = [
      ideaFixture({ id: "p1", pinned: true, order: 1 }),
      ideaFixture({ id: "p2", pinned: true, order: 3 }),
      ideaFixture({ id: "u1", pinned: false, order: 5 }),
    ];

    expect(nextIdeaOrder(ideas, true)).toBe(4);
    expect(nextIdeaOrder(ideas, false)).toBe(6);
  });

  it("parses provided fields and trims the title", () => {
    expect(parseIdeaPatch({ title: "  pinned idea  ", pinned: true, order: 2 })).toEqual({
      ok: true,
      value: { title: "pinned idea", pinned: true, order: 2 },
    });
  });

  it("rejects an invalid order and ignores a non-boolean pinned value", () => {
    expect(parseIdeaPatch({ order: 0 })).toEqual({ ok: false, error: { code: "INVALID_ORDER" } });
    expect(parseIdeaPatch({ pinned: "yes" })).toEqual({ ok: true, value: {} });
  });

  it("applies a patch without touching other fields", () => {
    const idea = ideaFixture({ title: "before", description: "memo", pinned: false });

    expect(applyIdeaPatch(idea, { pinned: true, order: 4 })).toMatchObject({
      title: "before",
      description: "memo",
      pinned: true,
      order: 4,
    });
  });
});
