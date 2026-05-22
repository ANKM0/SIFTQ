import { describe, expect, it } from "vitest";

import wireframeIndex from "../../docs/wireframes/index.html?raw";
import wireframeReadme from "../../docs/wireframes/README.md?raw";
import draggingWireframe from "../../docs/wireframes/matrix-dragging.html?raw";
import editingWireframe from "../../docs/wireframes/matrix-editing.html?raw";
import matrixWireframe from "../../docs/wireframes/matrix-mvp.html?raw";
import terminalDropWireframe from "../../docs/wireframes/matrix-terminal-drop.html?raw";
import cardsWireframe from "../../docs/wireframes/matrix-with-cards.html?raw";

describe("Matrix MVP wireframes", () => {
  it("keeps the documented six-area Matrix MVP layout", () => {
    const requiredLabels = [
      "Skipped",
      "Do",
      "Schedule",
      "Delegate",
      "Eliminate",
      "Done"
    ];

    const whenMissingLabels = requiredLabels.filter(
      (label) => !matrixWireframe.includes(`<h2>${label}</h2>`)
    );

    expect(whenMissingLabels).toEqual([]);
    expect(matrixWireframe).toContain('class="workspace"');
    expect(matrixWireframe).toContain('class="matrix-board"');
  });

  it("keeps task cards title-only while including explicit title editing UI", () => {
    const wireframeCorpus = [
      wireframeIndex,
      matrixWireframe,
      cardsWireframe,
      editingWireframe,
      draggingWireframe,
      terminalDropWireframe
    ].join("\n");

    expect(wireframeCorpus).toContain("card__title");
    expect(wireframeCorpus).not.toContain("card__meta");
    expect(wireframeIndex).toContain("matrix-editing.html");
    expect(editingWireframe).toContain("card-action");
    expect(editingWireframe).toContain(">Edit<");
    expect(editingWireframe).toContain('role="dialog"');
    expect(editingWireframe).toContain("Edit task title");
    expect(editingWireframe).toContain(">Save<");
    expect(editingWireframe).toContain(">Cancel<");
    expect(editingWireframe).not.toContain("Description");
  });

  it("documents terminal drops as hidden from the normal matrix display", () => {
    expect(terminalDropWireframe).toContain("Task hidden from matrix");
    expect(terminalDropWireframe).toContain("terminal-drop--complete");
    expect(terminalDropWireframe).not.toContain("wire-notes");
  });

  it("preserves CoDD traceability for the HTML wireframe set", () => {
    expect(wireframeReadme).toContain("node_id: design:matrix-mvp-wireframe");
    expect(wireframeReadme).toContain("matrix-mvp.html");
    expect(wireframeReadme).toContain("matrix-editing.html");
    expect(wireframeReadme).toContain("title-only task cards");
  });
});
