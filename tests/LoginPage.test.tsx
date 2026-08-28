import { describe, expect, it } from "vite-plus/test";
import { LoginPage, safeNextPath } from "../src/components/LoginPage";

describe("LoginPage", () => {
  it("renders the password form", () => {
    const html = String(<LoginPage />);

    expect(html).toContain('method="post"');
    expect(html).toContain('type="password"');
    expect(html).toContain('name="password"');
  });

  it("shows an error when authentication fails", () => {
    const html = String(<LoginPage error />);

    expect(html).toContain("Incorrect password");
  });
});

describe("safeNextPath", () => {
  it("keeps an internal path", () => {
    expect(safeNextPath("/tasks")).toBe("/tasks");
  });

  it("falls back for empty or external values", () => {
    expect(safeNextPath(undefined)).toBe("/");
    expect(safeNextPath("https://example.com")).toBe("/");
    expect(safeNextPath("//example.com")).toBe("/");
  });
});
