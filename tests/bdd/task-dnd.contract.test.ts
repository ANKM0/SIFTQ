import { describe, expect, it } from "vite-plus/test";
import app from "../../src/index";
import { taskFixture } from "../helpers/task-fixture";
import { MemoryTaskRepository } from "../helpers/memory-task-repository";

describe("Matrix drag and drop", () => {
  it("loads SortableJS and posts to the JSON reorder API", async () => {
    const repo = new MemoryTaskRepository();
    await repo.insert(taskFixture({ id: "task-1", status: "do", area: 1 }));

    const response = await app.request("/", undefined, {
      TASK_REPOSITORY: repo,
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain("sortablejs@1.15.6");
    expect(body).toContain("/matrix-dnd.js");
    expect(body).toContain('data-sortable-group="matrix"');
    expect(body).toContain('data-area="1"');
  });

  it("includes the conflict notice and restore hook", async () => {
    const repo = new MemoryTaskRepository();
    const response = await app.request("/matrix-dnd.js", undefined, {
      TASK_REPOSITORY: repo,
    });
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toMatch(/^application\/javascript/);
    expect(body).toContain("showDndConflict");
    expect(body).toContain("restoreMatrix");
    expect(body).toContain("/api/tasks/reorder");
  });
});
