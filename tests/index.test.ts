import { describe, expect, it } from "vite-plus/test";
import app from "../src/index";
import { authenticatedRequest } from "./helpers/authenticated-request";
import { MemoryTaskRepository } from "./helpers/memory-task-repository";

describe("smoke", () => {
  it("renders the Matrix root route", async () => {
    const response = await authenticatedRequest("/", new MemoryTaskRepository());

    expect(response.status).toBe(200);
    expect(await response.text()).toContain("Matrix");
  });

  it("serves the HTMX conflict response handler without authentication", async () => {
    const response = await app.request("/htmx-conflict.js");

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("application/javascript");
    expect(await response.text()).toContain("xhr.status !== 409");
  });
});
