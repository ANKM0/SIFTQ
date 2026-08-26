import { describe, expect, it } from "vitest";
import app from "../src/index";

describe("smoke", () => {
  it("returns ok from the root route", async () => {
    const response = await app.request("/");

    expect(response.status).toBe(200);
    expect(await response.text()).toBe("ok");
  });
});
