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
