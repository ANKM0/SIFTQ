import { describe, expect, it } from "vite-plus/test";
import app from "../src/index";
import { MemoryTaskRepository } from "./helpers/memory-task-repository";

describe("smoke", () => {
  it("renders the Matrix root route", async () => {
    const response = await app.request("/", undefined, {
      TASK_REPOSITORY: new MemoryTaskRepository(),
    });

    expect(response.status).toBe(200);
    expect(await response.text()).toContain("Matrix");
  });
});
