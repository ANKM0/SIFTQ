import { describe, expect, it } from "vitest";

import markdownChecker from "../../scripts/ci/check_markdown.py?raw";

describe("Markdown CI contract", () => {
  it("excludes generated sympohy run artifacts from Markdown checks", () => {
    expect(markdownChecker).toContain('".sympohy"');
    expect(markdownChecker).toContain("EXCLUDED_DIRS");
    expect(markdownChecker).toContain("if any(part in EXCLUDED_DIRS for part in path.parts)");
  });
});
