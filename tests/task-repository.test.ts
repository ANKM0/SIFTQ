import { describe, expect, it } from "vite-plus/test";
import { D1TaskRepository } from "../src/task-repository";

describe("D1TaskRepository", () => {
  it("is not implemented yet", async () => {
    const repository = new D1TaskRepository();

    await expect(repository.list()).rejects.toThrow("not implemented");
  });
});
