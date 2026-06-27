import { describe, expect, it } from "vitest";

import wireframeIndex from "../../docs/wireframes/index.html?raw";
import wireframeReadme from "../../docs/wireframes/README.md?raw";
import createWireframe from "../../docs/wireframes/matrix-create.html?raw";
import draggingWireframe from "../../docs/wireframes/matrix-dragging.html?raw";
import editingWireframe from "../../docs/wireframes/matrix-editing.html?raw";
import emptyWireframe from "../../docs/wireframes/matrix-empty.html?raw";
import matrixWireframe from "../../docs/wireframes/matrix-mvp.html?raw";
import terminalDropWireframe from "../../docs/wireframes/matrix-terminal-drop.html?raw";
import cardsWireframe from "../../docs/wireframes/matrix-with-cards.html?raw";
import taskDeleteWireframe from "../../docs/wireframes/task-delete-confirm.html?raw";
import taskDetailWireframe from "../../docs/wireframes/task-detail.html?raw";
import taskDeletedWireframe from "../../docs/wireframes/task-list-deleted.html?raw";
import taskDraggingWireframe from "../../docs/wireframes/task-list-dragging.html?raw";
import taskStatusMenuWireframe from "../../docs/wireframes/task-list-status-menu.html?raw";
import taskListContract from "../../docs/wireframes/task-list-v3.md?raw";
import taskListWireframe from "../../docs/wireframes/task-list.html?raw";
import taskNotFoundWireframe from "../../docs/wireframes/task-not-found.html?raw";

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

  it("keeps matrix task cards title-only while including explicit task editing UI", () => {
    const wireframeCorpus = [
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
    expect(editingWireframe).toContain("Edit task");
    expect(editingWireframe).toContain("Description");
    expect(editingWireframe).toContain("<textarea>");
    expect(editingWireframe).toContain(">Save<");
    expect(editingWireframe).toContain(">Cancel<");
    expect(editingWireframe).toContain('onclick="location.href=\'./matrix-with-cards.html\'"');
    expect(editingWireframe).toContain('class="button-primary" type="button"');
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

  it("documents the task list as draggable list cards", () => {
    expect(wireframeIndex).toContain("task-list.html");
    expect(wireframeIndex).toContain("task-detail.html");
    expect(wireframeIndex).not.toMatch(/\bv3\b/i);
    expect(taskListContract).toContain("node_id: design:task-list-v3-wireframe");
    expect(wireframeReadme).toContain("draggable list card");
    expect(taskListWireframe).toContain("task-list-card");
    expect(taskListWireframe).toContain("task-list-card--active");
    expect(taskListWireframe).toContain("task-list-card--done");
    expect(taskListWireframe).toContain("task-list-card--skipped");
    expect(taskListWireframe).not.toMatch(/task-list-card--do(?:\s|")/);
    expect(taskListWireframe).not.toMatch(/task-list-card--schedule(?:\s|")/);
    expect(taskListWireframe).not.toMatch(/task-list-card--delegate(?:\s|")/);
    expect(taskListWireframe).not.toMatch(/task-list-card--eliminate(?:\s|")/);
    expect(taskListWireframe).toContain("drag-handle");
    expect(taskListWireframe).toContain(">Do</button>");
    expect(taskListWireframe).toContain(">Schedule</button>");
    expect(taskListWireframe).toContain("task-list-card__description");
    expect(taskListWireframe).toContain("説明なし");
    expect(taskListWireframe).toContain("status-button");
    expect(taskListWireframe).toContain('href="./task-list-status-menu.html"');
    expect(taskListWireframe).toContain("active ▾");
    expect(taskListWireframe).toContain("done ▾");
    expect(taskListWireframe).toContain("skipped ▾");
    expect(taskListWireframe).not.toContain("<select");
    expect(wireframeIndex).toContain("task-list-status-menu.html");
    expect(taskStatusMenuWireframe).toContain("status-menu");
    expect(taskStatusMenuWireframe).toContain('role="menu"');
    expect(taskStatusMenuWireframe).toContain('aria-expanded="true"');
    expect(taskStatusMenuWireframe).toContain('href="./task-list.html"');
    expect(taskStatusMenuWireframe).toContain(">active</a>");
    expect(taskStatusMenuWireframe).toContain(">done</a>");
    expect(taskStatusMenuWireframe).toContain(">skipped</a>");
    expect(taskListWireframe).not.toContain("::");
    expect(taskListWireframe).toContain(">詳細<");
    expect(taskListWireframe).toContain(">削除<");
    expect(taskListWireframe).not.toContain("status-filter");
    expect(taskListWireframe).not.toContain("作成日時");
    expect(taskListWireframe).not.toContain("更新日時");
  });

  it("keeps Matrix and Tasks navigation available from every app wireframe", () => {
    const appWireframes = [
      matrixWireframe,
      emptyWireframe,
      createWireframe,
      cardsWireframe,
      editingWireframe,
      draggingWireframe,
      terminalDropWireframe,
      taskListWireframe,
      taskDeletedWireframe,
      taskDraggingWireframe,
      taskStatusMenuWireframe,
      taskDetailWireframe,
      taskDeleteWireframe,
      taskNotFoundWireframe
    ];

    for (const appWireframe of appWireframes) {
      expect(appWireframe).toContain('aria-label="Primary"');
      expect(appWireframe).toContain(">マトリックス<");
      expect(appWireframe).toContain(">タスク一覧<");
      expect(appWireframe).toContain(">インデックス<");
    }

    expect(wireframeIndex).toContain('href="./matrix-mvp.html"');
    expect(wireframeIndex).toContain('href="./task-list.html"');
  });

  it("documents task list reorder, detail, delete, and missing-task states", () => {
    expect(taskDraggingWireframe).toContain("listOrder のみ");
    expect(taskDraggingWireframe).toContain("task-list-drop-slot");
    expect(taskDetailWireframe).toContain("説明");
    expect(taskDetailWireframe).toContain("エリア");
    expect(taskDetailWireframe).toContain("ステータス");
    expect(taskDetailWireframe).toContain("作成日時");
    expect(taskDetailWireframe).toContain("更新日時");
    expect(taskDetailWireframe).toContain("⇦ 一覧へ戻る");
    expect(taskDeleteWireframe).toContain("タスクを削除しますか?");
    expect(taskDeleteWireframe).toContain("Fix terminal drop");
    expect(taskDeleteWireframe).toContain(">キャンセル<");
    expect(taskDeleteWireframe).toContain(">削除<");
    expect(taskDeleteWireframe).toContain('href="./task-list-deleted.html"');
    expect(taskDeleteWireframe).not.toContain('href="./task-not-found.html"');
    expect(taskDeleteWireframe).not.toContain("Delete permanently");
    expect(wireframeIndex).toContain("task-list-deleted.html");
    expect(taskDeletedWireframe).toContain("タスクを削除しました");
    expect(taskDeletedWireframe).toContain('role="status"');
    expect(taskDeletedWireframe).not.toContain("Fix terminal drop");
    expect(taskNotFoundWireframe).toContain("タスクが見つかりません");
    expect(taskNotFoundWireframe).toContain("タスク一覧へ戻る");
  });
});
