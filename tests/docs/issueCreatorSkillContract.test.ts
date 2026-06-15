import { execFileSync } from "node:child_process";
import { describe, expect, it } from "vitest";

import agentConfig from "../../.codex/skills/issue-creator/agents/openai.yaml?raw";
import skill from "../../.codex/skills/issue-creator/SKILL.md?raw";
import labelPolicy from "../../.codex/skills/issue-creator/references/issue-label-policy.md?raw";
import issueTemplates from "../../.codex/skills/issue-creator/references/issue-templates.md?raw";

const requiredSkillFiles = [
  ".codex/skills/issue-creator/SKILL.md",
  ".codex/skills/issue-creator/agents/openai.yaml",
  ".codex/skills/issue-creator/references/issue-label-policy.md",
  ".codex/skills/issue-creator/references/issue-templates.md"
];

describe("Issue creator skill contract", () => {
  it("keeps every Issue #94 deliverable tracked", () => {
    const trackedFiles = execFileSync("git", [
      "ls-files",
      ".codex/skills/issue-creator"
    ], { encoding: "utf8" }).trim().split("\n");

    expect(trackedFiles.sort()).toEqual([...requiredSkillFiles].sort());
  });

  it("defines the skill, templates, labels, and agent prompt", () => {
    expect(skill).toContain("name: issue-creator");
    expect(skill).toContain("## Workflow");
    expect(skill).toContain("## Quality Bar");

    expect(issueTemplates).toContain("## Feature Change");
    expect(issueTemplates).toContain("## Research");
    expect(issueTemplates).toContain("## Bug");

    expect(labelPolicy).toContain("sympohy:pending");
    expect(labelPolicy).toContain("sympohy:phase:triage");
    expect(labelPolicy).toContain("Automation-Owned Labels");

    expect(agentConfig).toContain('display_name: "Issue Creator"');
    expect(agentConfig).toContain("default_prompt:");
  });
});
