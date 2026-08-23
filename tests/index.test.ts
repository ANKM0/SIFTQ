import { describe, expect, it } from "vitest";
import app from "../src/index";

describe("GET /", () => {
  it("returns the initial SIFTQ HTML without a React client root", async () => {
    const response = await app.request("/");

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toMatch(/^text\/html/);

    const body = await response.text();

    expect(body).toContain("SIFTQ");
    expect(body).toContain("<h1>SIFTQ</h1>");
    expect(body).not.toMatch(/\bid=["']root["']/i);
    expect(body).not.toContain("createRoot");
    expect(body).not.toMatch(/<script\b/i);
  });
});
