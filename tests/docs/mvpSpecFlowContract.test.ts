import { describe, expect, it } from "vitest";

import mvpSpecFlow from "../../docs/contributing/mvp-spec-flow.md?raw";

describe("MVP spec flow", () => {
  it("defines the required wireframe markdown template anchors", () => {
    const requiredAnchors = [
      "## Wireframe Markdown Template",
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
});
