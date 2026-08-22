import { describe, expect, it } from "vitest";

import app from "../src/index";

describe("Worker initial screen", () => {
  it("renders the initial screen as HTML without a client-side root", async () => {
    const response = await app.request("http://localhost/");
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("text/html");
    expect(body).toContain("<h1>SIFTQ</h1>");
    expect(body).not.toContain('id="root"');
    expect(body).not.toContain("<script");
  });
});
