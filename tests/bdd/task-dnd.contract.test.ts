import { describe, expect, it } from "vite-plus/test";
import { authenticatedRequest } from "../helpers/authenticated-request";
import { taskFixture } from "../helpers/task-fixture";
import { createMemoryTaskRepository } from "../helpers/memory-task-repository";

describe("Matrix drag and drop", () => {
  it("enables native drag and drop and posts to the JSON reorder API", async () => {
    const repo = createMemoryTaskRepository();
    await repo.insert(taskFixture({ id: "task-1", status: "do", area: 1 }));

    const response = await authenticatedRequest("/", repo);
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).not.toContain("sortablejs");
    expect(body).toContain("/matrix-dnd.js");
    expect(body).toContain('data-dnd-group="matrix"');
    expect(body).toContain('data-area="1"');
  });

  it("includes the conflict notice and restore hook", async () => {
    const repo = createMemoryTaskRepository();
    const response = await authenticatedRequest("/matrix-dnd.js", repo);
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toMatch(/^application\/javascript/);
    expect(body).toContain("showDndConflict");
    expect(body).toContain("restoreMatrix");
    expect(body).toContain("/api/tasks/reorder");
    expect(body).toContain("dragstart");
    expect(body).toContain("dragover");
    expect(body).toContain("drop");
    expect(body).toContain("matrixDropIndex");
    expect(body).not.toContain("setDragImage");
    expect(body).toContain("setMatrixDndPending(true)");
    expect(body).toContain("finally(function () { setMatrixDndPending(false); })");
    expect(body).toContain('card.setAttribute("draggable", pending ? "false" : "true")');
    expect(body).toContain("Array.isArray(tasks)");
    expect(body).toContain('updatedCard.setAttribute("data-version", String(task.version))');
  });

  it("resolves drag targets from the whole quadrant", async () => {
    const repo = createMemoryTaskRepository();
    const response = await authenticatedRequest("/matrix-dnd.js", repo);
    const body = await response.text();
    const targetResolution = "var target = matrixDropList(event);";

    expect(response.status).toBe(200);
    expect(body).toContain("function matrixDropList(event) {");
    expect(body).toContain('var quadrant = event.target.closest(".area--quadrant[data-drop-area]");');
    expect(body).toContain('return quadrant ? quadrant.querySelector(".matrix-cards[data-dnd-group]") : null;');
    expect(body.split(targetResolution).length - 1).toBe(2);
  });

  it("includes Matrix status and delete actions", async () => {
    const repo = createMemoryTaskRepository();
    const response = await authenticatedRequest("/matrix-dnd.js", repo);
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain('contextmenu');
    expect(body).toContain('method: "PATCH"');
    expect(body).toContain('method: "DELETE"');
    expect(body).toContain('"/api/tasks/"');
    expect(body).toContain('このタスクを削除しますか？');
    expect(body).toContain('textContent = "キャンセル"');
    expect(body).toContain('textContent = "削除"');
    expect(body).toContain("matrix-modal-backdrop");
  });
});

describe("Matrix drag and drop resilience", () => {
  it("defers the dropped card move until the native drag session ends", async () => {
    const repo = createMemoryTaskRepository();
    const response = await authenticatedRequest("/matrix-dnd.js", repo);
    const body = await response.text();
    const start = body.indexOf('document.addEventListener("drop"');
    const end = body.indexOf('document.addEventListener("dragend"');
    const dropHandler = body.slice(start, end);

    expect(response.status).toBe(200);
    expect(start).toBeGreaterThan(-1);
    expect(end).toBeGreaterThan(start);

    // Moving the drag source inside the drop handler makes some browsers end
    // the drag without firing dragend, leaving the whole page inert. The move
    // must be deferred and every drop path must clear the drag state.
    expect(dropHandler).toContain("clearMatrixDnd();");
    expect(dropHandler).toContain("if (!target) { clearMatrixDnd(); return; }");
    expect(dropHandler.indexOf("setTimeout")).toBeGreaterThan(-1);
    expect(dropHandler.indexOf("setTimeout")).toBeLessThan(dropHandler.indexOf("target.insertBefore"));
    expect(body).toContain('document.addEventListener("dragend", clearMatrixDnd);');
  });
});
