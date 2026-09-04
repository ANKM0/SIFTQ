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

  it("serves the popover dismissal handler without authentication", async () => {
    const response = await app.request("/popover-dismiss.js");

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("application/javascript");
    const body = await response.text();
    expect(body).toContain("window.location.assign");
    expect(body).toContain("[data-popover-close]");
    expect(body).toContain("[data-popover-cancel]");
  });

  it("serves the matrix area navigation handler without authentication", async () => {
    const response = await app.request("/matrix-dnd.js");

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("application/javascript");
    const body = await response.text();
    expect(body).toContain('closest(".area--quadrant[data-drop-area]")');
    expect(body).toContain('window.location.assign("/tasks/new?area=" + encodeURIComponent(area) + "&from=matrix")');
  });
});
