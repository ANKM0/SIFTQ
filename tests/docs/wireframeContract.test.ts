import { describe, expect, it } from "vitest";

import wireframeIndex from "../../docs/wireframes/index.html?raw";
import wireframeReadme from "../../docs/wireframes/README.md?raw";
import draggingWireframe from "../../docs/wireframes/matrix-dragging.html?raw";
import editingWireframe from "../../docs/wireframes/matrix-editing.html?raw";
import matrixWireframe from "../../docs/wireframes/matrix-mvp.html?raw";
import terminalDropWireframe from "../../docs/wireframes/matrix-terminal-drop.html?raw";
import cardsWireframe from "../../docs/wireframes/matrix-with-cards.html?raw";
import taskDeleteConfirmWireframe from "../../docs/wireframes/task-delete-confirm.html?raw";
import taskDetailWireframe from "../../docs/wireframes/task-detail.html?raw";
import taskNotFoundWireframe from "../../docs/wireframes/task-not-found.html?raw";
import taskListDeletedWireframe from "../../docs/wireframes/task-list-deleted.html?raw";
import taskListDraggingWireframe from "../../docs/wireframes/task-list-dragging.html?raw";
import taskListStatusMenuWireframe from "../../docs/wireframes/task-list-status-menu.html?raw";
import taskListWireframe from "../../docs/wireframes/task-list.html?raw";
import taskListV3Spec from "../../docs/wireframes/task-list-v3.md?raw";

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

describe("Task list v3 wireframes", () => {
  it("documents the task list v3 contract and linked HTML states", () => {
    expect(taskListV3Spec).toContain("node_id: design:task-list-v3-wireframe");
    expect(taskListV3Spec).toContain("task-list.html");
    expect(taskListV3Spec).toContain("task-list-dragging.html");
    expect(taskListV3Spec).toContain("task-list-status-menu.html");
    expect(taskListV3Spec).toContain("task-list-deleted.html");
    expect(taskListV3Spec).toContain("task-detail.html");
    expect(taskListV3Spec).toContain("task-delete-confirm.html");
    expect(taskListV3Spec).toContain("task-not-found.html");
    expect(taskListV3Spec).toContain("area ラベルを含む drag handle");
    expect(taskListV3Spec).toContain("削除済み task の placeholder");
  });

  it("keeps the list view as a draggable card list with handle-only area labels", () => {
    expect(taskListWireframe).toContain("<h1>タスク一覧</h1>");
    expect(taskListWireframe).toContain(">マトリックス<");
    expect(taskListWireframe).toContain('aria-label="task list"');
    expect(taskListWireframe).not.toContain("<table");
    expect(taskListWireframe).toContain("handle__area");
    expect(taskListWireframe).toContain("説明なし");
    expect(taskListWireframe).toContain(">active<");
    expect(taskListWireframe).toContain(">done<");
    expect(taskListWireframe).toContain(">skipped<");
    expect(taskListWireframe).toContain(">詳細<");
    expect(taskListWireframe).toContain(">削除<");
    expect(taskListWireframe).not.toContain("タスクを削除しました");
  });

  it("covers drag, status-menu, deleted, detail, delete-confirm, and not-found states", () => {
    expect(taskListDraggingWireframe).toContain("Drop target for reordered position");
    expect(taskListDraggingWireframe).toContain("handle__area");

    expect(taskListStatusMenuWireframe).toContain('role="menu"');
    expect(taskListStatusMenuWireframe).toContain(">active<");
    expect(taskListStatusMenuWireframe).toContain(">done<");
    expect(taskListStatusMenuWireframe).toContain(">skipped<");

    expect(taskListDeletedWireframe).toContain("タスクを削除しました");
    expect(taskListDeletedWireframe).not.toContain("Deleted task placeholder");
    expect(taskListDeletedWireframe).not.toContain("復元");

    expect(taskDetailWireframe).toContain("作成日時");
    expect(taskDetailWireframe).toContain("更新日時");
    expect(taskDetailWireframe).toContain(">保存<");
    expect(taskDetailWireframe).toContain(">削除<");

    expect(taskDeleteConfirmWireframe).toContain('role="dialog"');
    expect(taskDeleteConfirmWireframe).toContain('"Fix browser storage migration" を削除しますか?');
    expect(taskDeleteConfirmWireframe).toContain("復元操作はありません");

    expect(taskNotFoundWireframe).toContain("タスクが見つかりませんでした");
    expect(taskNotFoundWireframe).toContain("タスク一覧へ戻る");
  });

  it("keeps the index and README wired to both matrix and task list states", () => {
    expect(wireframeReadme).toContain("task-list-v3.md");
    expect(wireframeReadme).toContain(
      "task list / detail / delete / not found contract for Issue #68"
    );
    expect(wireframeIndex).toContain("task-list.html");
    expect(wireframeIndex).toContain("task-detail.html");
  });
});
