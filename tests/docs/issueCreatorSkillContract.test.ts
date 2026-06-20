import { describe, expect, it } from "vitest";

import agentConfig from "../../.codex/skills/issue-creator/agents/openai.yaml?raw";
import skill from "../../.codex/skills/issue-creator/SKILL.md?raw";
import labelPolicy from "../../.codex/skills/issue-creator/references/issue-label-policy.md?raw";
import issueTemplates from "../../.codex/skills/issue-creator/references/issue-templates.md?raw";

const requiredSkillFiles = [
  [".codex/skills/issue-creator/SKILL.md", skill],
  [".codex/skills/issue-creator/agents/openai.yaml", agentConfig],
  [
    ".codex/skills/issue-creator/references/issue-label-policy.md",
    labelPolicy
  ],
  [
    ".codex/skills/issue-creator/references/issue-templates.md",
    issueTemplates
  ]
];

describe("Issue creator skill contract", () => {
  it("keeps every Issue #94 deliverable loadable", () => {
    expect(requiredSkillFiles).toHaveLength(4);
    for (const [path, content] of requiredSkillFiles) {
      expect(path).toContain(".codex/skills/issue-creator");
      expect(content.trim().length).toBeGreaterThan(0);
    }
  });

  it("defines the skill, templates, labels, and agent prompt", () => {
    expect(skill).toContain("name: siftq-issue-creator");
    expect(skill).toContain("## 1) Issue creation workflow");
    expect(skill).toContain("## 2) Label rule (this repository)");
    expect(skill).toContain("## 3) Required output format");

    expect(issueTemplates).toContain("## Feature Change テンプレート");
    expect(issueTemplates).toContain("## Scope");
    expect(issueTemplates).toContain("やること");
    expect(issueTemplates).toContain("やらないこと");
    expect(issueTemplates).toContain("## AC");
    expect(issueTemplates).toContain("## DoD");
    expect(issueTemplates).toContain("## Research テンプレート");
    expect(issueTemplates).toContain("## Bug テンプレート");

    expect(labelPolicy).toContain("sympohy:pending");
    expect(labelPolicy).toContain("sympohy:phase:triage");
    expect(labelPolicy).toContain("## Forbidden as manual assignment");

    expect(agentConfig).toContain('display_name: "SIFTQ Issue Creator"');
    expect(agentConfig).toContain("default_prompt:");
  });
});
