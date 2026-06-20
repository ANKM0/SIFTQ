import { describe, expect, it } from "vitest";

import branchStrategy from "../../docs/contributing/branch-strategy.md?raw";
import commitMessageFormat from "../../docs/contributing/commit-message-format.md?raw";
import workflowSourceDesign from "../../docs/design/contributing-workflow-source-of-truth.md?raw";

describe("contributing workflow source of truth", () => {
  it("keeps branch and commit references on canonical contributing docs", () => {
    expect(branchStrategy).toContain(
      "Implementation-time agents must use this document"
    );
    expect(commitMessageFormat).toContain(
      "Implementation-time agents must use this document"
    );
    expect(workflowSourceDesign).toContain("docs/contributing/branch-strategy.md");
    expect(workflowSourceDesign).toContain(
      "docs/contributing/commit-message-format.md"
    );
  });

  it("does not link docs to removed dedicated workflow skills", () => {
    const auditedDocs = [
      branchStrategy,
      commitMessageFormat,
      workflowSourceDesign
    ].join("\n");

    expect(auditedDocs).not.toContain(".agents/skills/branch-strategy/SKILL.md");
    expect(auditedDocs).not.toContain(
      ".agents/skills/commit-message-format/SKILL.md"
    );
    expect(auditedDocs).not.toContain(".agents/skills/commit-message-format/");
  });
});
