import { describe, expect, it } from "vitest";

import adrAuthoring from "../../docs/contributing/adr-authoring.md?raw";
import pullRequestTemplate from "../../.github/pull_request_template.md?raw";
import mvpSpecFlow from "../../docs/contributing/mvp-spec-flow.md?raw";

describe("MVP spec flow", () => {
  it("defines the required wireframe markdown template anchors", () => {
    const requiredAnchors = [
      "## Wireframe Markdown Template",
      "wireframe CoDD node の命名規則は `design:<feature-wireframe>`",
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
      (anchor) => !mvpSpecFlow.includes(anchor)
    );

    expect(missingAnchors).toEqual([]);
  });

  it("requires UI-changing PRs to update wireframe HTML", () => {
    const requiredRuleFragments = [
      "UI 変更 PR では",
      "wireframe HTML を",
      "更新する",
      "`tests/docs/wireframeContract.test.ts`"
    ];

    const missingSpecFragments = requiredRuleFragments.filter(
      (fragment) => !mvpSpecFlow.includes(fragment)
    );

    expect(missingSpecFragments).toEqual([]);
    expect(pullRequestTemplate).toContain(
      "UI 変更がある場合は wireframe HTML を更新し"
    );
    expect(pullRequestTemplate).toContain(
      "`tests/docs/wireframeContract.test.ts`"
    );
  });

  it("documents when an ADR is required", () => {
    const requiredAdrFragments = [
      "次のどちらかに該当する場合は、ADR を作成する",
      "複数機能、複数ドキュメント、または repository workflow",
      "後から変えると migration、schema 変更、toolchain 移行",
      "runtime 変更、storage 移行、または architecture boundary",
      "ADR が必要になる代表例",
      "アーキテクチャ判断",
      "主要モジュール",
      "ライブラリ",
      "ツール",
      "governance"
    ];

    const missingAdrFragments = requiredAdrFragments.filter(
      (fragment) => !mvpSpecFlow.includes(fragment)
    );

    expect(missingAdrFragments).toEqual([]);
  });

  it("documents the boundary between ADRs and design docs", () => {
    const requiredBoundaryFragments = [
      "### ADR / Design Doc Boundary",
      "判断の寿命と適用範囲",
      "ADR は durable decision を記録する",
      "Design doc は feature-specific application を記録する",
      "Design doc は ADR の判断を再決定してはならない",
      "ADR は feature-specific implementation details を持たない"
    ];

    const missingBoundaryFragments = requiredBoundaryFragments.filter(
      (fragment) => !mvpSpecFlow.includes(fragment)
    );

    expect(missingBoundaryFragments).toEqual([]);
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
    expect(adrAuthoring).toContain(
      "perspectives, and application of existing ADRs"
    );
    expect(mvpSpecFlow).toContain("per-feature");
    expect(mvpSpecFlow).toContain("external design");
    expect(mvpSpecFlow).toContain("internal design");
    expect(mvpSpecFlow).toContain("test perspectives");
    expect(mvpSpecFlow).toContain("既存 ADR の");
    expect(mvpSpecFlow).toContain("application");
  });
});
