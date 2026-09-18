import { describe, expect, it } from "vite-plus/test";
import { authenticatedRequest } from "../helpers/authenticated-request";
import { taskFixture } from "../helpers/task-fixture";
import { createMemoryTaskRepository } from "../helpers/memory-task-repository";

describe("Matrix drag and drop", () => {
  it("exposes pointer drag hooks and posts to the JSON reorder API", async () => {
    const repo = createMemoryTaskRepository();
    await repo.insert(taskFixture({ id: "task-1", status: "do", area: 1 }));

    const response = await authenticatedRequest("/", repo);
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain("/matrix-dnd.js");
    expect(body).toContain('data-dnd-group="matrix"');
    expect(body).toContain('data-area="1"');
  });

  it("uses pointer events instead of the native HTML5 drag session", async () => {
    const repo = createMemoryTaskRepository();
    const response = await authenticatedRequest("/matrix-dnd.js", repo);
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toMatch(/^application\/javascript/);
    for (const pointerEvent of ["pointerdown", "pointermove", "pointerup", "pointercancel"]) {
      expect(body).toContain(`document.addEventListener("${pointerEvent}"`);
    }
    expect(body).toContain("setPointerCapture");
    expect(body).toContain("elementFromPoint");
    expect(body).toContain("MATRIX_DRAG_THRESHOLD");
    expect(body).toContain("matrixDropIndex");
    for (const nativeMarker of ["dragstart", "dragover", "dataTransfer", "setDragImage"]) {
      expect(body).not.toContain(nativeMarker);
    }
    expect(body).toContain("showDndConflict");
    expect(body).toContain("restoreMatrix");
    expect(body).toContain("/api/tasks/reorder");
    expect(body).toContain("setMatrixDndPending(true)");
    expect(body).toContain("finally(function () { setMatrixDndPending(false); })");
    expect(body).toContain("Array.isArray(tasks)");
    expect(body).toContain('updatedCard.setAttribute("data-version", String(task.version))');
  });

  it("resolves drag targets from the whole quadrant", async () => {
    const repo = createMemoryTaskRepository();
    const response = await authenticatedRequest("/matrix-dnd.js", repo);
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain("function matrixDropListFromPoint(x, y) {");
    expect(body).toContain("document.elementFromPoint(x, y)");
    expect(body).toContain('element.closest(".area--quadrant[data-drop-area]")');
    expect(body).toContain('quadrant.querySelector(".matrix-cards[data-dnd-group]")');
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
  it("suppresses the click that follows a pointer drag", async () => {
    const repo = createMemoryTaskRepository();
    const response = await authenticatedRequest("/matrix-dnd.js", repo);
    const body = await response.text();
    const start = body.indexOf('document.addEventListener("click", function (event) {');
    const end = body.indexOf('document.addEventListener("click", function (event) {', start + 1);
    const suppressionHandler = body.slice(start, end);

    expect(response.status).toBe(200);
    expect(start).toBeGreaterThan(-1);
    expect(end).toBeGreaterThan(start);

    // The first click after a drop must be swallowed so the card does not
    // navigate to the task detail while the pointer is still settling.
    expect(suppressionHandler).toContain("if (!suppressMatrixCardClick) return;");
    expect(suppressionHandler).toContain("event.preventDefault();");
    expect(suppressionHandler).toContain("suppressMatrixCardClick = false;");
    expect(body).toContain("function finishMatrixDrag(event) {");
    expect(body).toContain("setTimeout(function () { suppressMatrixCardClick = false; }, 0);");
  });

  it("auto-scrolls the quadrant when the pointer nears its edge", async () => {
    const repo = createMemoryTaskRepository();
    const response = await authenticatedRequest("/matrix-dnd.js", repo);
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain("function updateMatrixAutoScroll(pointerY, list) {");
    expect(body).toContain("list.scrollHeight <= list.clientHeight");
    expect(body).toContain("requestAnimationFrame(stepMatrixAutoScroll)");
    expect(body).toContain("matrixAutoScrollList.scrollTop += matrixAutoScrollDelta * 14;");
  });
});
