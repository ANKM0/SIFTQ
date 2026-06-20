import { describe, expect, it } from "vitest";

import pullRequestTemplate from "../../.github/pull_request_template.md?raw";
import featureDocsPlanning from "../../.agents/skills/feature-docs-planning/SKILL.md?raw";
import adrAuthoring from "../../docs/contributing/adr-authoring.md?raw";
import designTemplate from "../../docs/design/templates/design.md?raw";
import requirementsTemplate from "../../docs/requirements/templates/requirements.md?raw";
import wireframeTemplate from "../../docs/wireframes/templates/wireframe.md?raw";

describe("feature documentation artifacts", () => {
  it("defines the required wireframe markdown template anchors", () => {
    const requiredAnchors = [
      "# Wireframe Template",
      "node_id: design:<feature-wireframe>",
      "## Target HTML（対象HTML）",
      "## UI Contract（UI契約）",
      "## States（状態）",
      "## Copy and Layout（文言とレイアウト）",
      "## Contract Test（契約テスト）",
      "## Open Questions（未決事項）",
      "`tests/docs/wireframeContract.test.ts`"
    ];

    const missingAnchors = requiredAnchors.filter(
      (anchor) => !wireframeTemplate.includes(anchor)
    );

    expect(missingAnchors).toEqual([]);
  });

  it("requires UI-changing PRs to update wireframe HTML", () => {
    expect(pullRequestTemplate).toContain(
      "UI 変更がある場合は wireframe HTML を更新し"
    );
    expect(pullRequestTemplate).toContain(
      "`tests/docs/wireframeContract.test.ts`"
    );
  });

  it("documents when an ADR is required", () => {
    const requiredAdrFragments = [
      "Create or update an ADR when either condition applies",
      "multiple features, multiple documents, or repository",
      "migration, schema changes",
      "runtime changes, storage migration, or architecture",
      "architecture decisions",
      "major modules",
      "libraries",
      "tools",
      "governance"
    ];

    const missingAdrFragments = requiredAdrFragments.filter(
      (fragment) => !adrAuthoring.includes(fragment)
    );

    expect(missingAdrFragments).toEqual([]);
  });

  it("documents the boundary between ADRs and design docs", () => {
    expect(adrAuthoring).toContain("## Boundary With Design Docs");
    expect(adrAuthoring).toContain("Use ADRs for durable decisions");
    expect(adrAuthoring).toContain("architecture decisions");
    expect(adrAuthoring).toContain("major modules");
    expect(adrAuthoring).toContain("libraries, tools, runtime, storage");
    expect(adrAuthoring).toContain("schema, migration, toolchain, governance");
    expect(adrAuthoring).toContain("architecture boundaries");
    expect(adrAuthoring).toContain(
      "Use design docs for feature-specific application"
    );
    expect(adrAuthoring).toContain(
      "Design docs must not re-decide ADR decisions"
    );
    expect(adrAuthoring).toContain("per-feature external design");
    expect(adrAuthoring).toContain("internal design");
    expect(adrAuthoring).toContain("test perspectives");
  });

  it("keeps template responsibilities in the artifact templates", () => {
    expect(requirementsTemplate).toContain("## 背景");
    expect(requirementsTemplate).toContain("## 概要");
    expect(requirementsTemplate).toContain("## 機能要件");
    expect(requirementsTemplate).toContain("## 非機能要件");
    expect(requirementsTemplate).toContain("## 関連Issue");
    expect(requirementsTemplate).toContain("AC / DoD の正は Issue 側に置く");
    expect(requirementsTemplate).not.toContain("## Acceptance Criteria");
    expect(designTemplate).toContain("## External Design（外部設計）");
    expect(designTemplate).toContain("## Internal Design（内部設計）");
    expect(designTemplate).toContain("## Test Viewpoints（テスト観点）");
    expect(designTemplate).toContain("## ADR Application（ADR 適用）");
  });

  it("documents artifact decision outcomes in the feature docs skill", () => {
    expect(featureDocsPlanning).toContain("docs/contributing/development-flow.md");
    expect(featureDocsPlanning).toContain("development-flow diagram");
    expect(featureDocsPlanning).toContain("new");
    expect(featureDocsPlanning).toContain("existing");
    expect(featureDocsPlanning).toContain("not needed");
    expect(featureDocsPlanning).toContain(
      "docs/requirements/templates/requirements.md"
    );
    expect(featureDocsPlanning).toContain("docs/design/templates/design.md");
    expect(featureDocsPlanning).toContain("docs/wireframes/templates/wireframe.md");
  });
});
