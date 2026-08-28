import { describe, expect, it } from "vite-plus/test";
import { authenticatedRequest } from "./helpers/authenticated-request";
import { MemoryTaskRepository } from "./helpers/memory-task-repository";

describe("smoke", () => {
  it("renders the Matrix root route", async () => {
    const response = await authenticatedRequest("/", new MemoryTaskRepository());

    expect(response.status).toBe(200);
    expect(await response.text()).toContain("Matrix");
  });
});
