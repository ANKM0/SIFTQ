import { describe, expect, it } from "vite-plus/test";
import { createSession, isPasswordValid, isValidSession } from "../src/auth";

describe("session signing", () => {
  it("accepts a session signed with the same secret", async () => {
    const session = await createSession("secret", Date.now() + 60_000);

    expect(await isValidSession("secret", session)).toBe(true);
  });

  it("rejects a session signed with a different secret", async () => {
    const session = await createSession("secret-a", Date.now() + 60_000);

    expect(await isValidSession("secret-b", session)).toBe(false);
  });

  it("rejects an expired session", async () => {
    const session = await createSession("secret", Date.now() - 1_000);

    expect(await isValidSession("secret", session)).toBe(false);
  });

  it("rejects a tampered signature", async () => {
    const session = await createSession("secret", Date.now() + 60_000);
    const tampered = session.slice(0, -1) + (session.endsWith("a") ? "b" : "a");

    expect(await isValidSession("secret", tampered)).toBe(false);
  });
});

describe("password validation", () => {
  it("accepts the expected password", async () => {
    expect(await isPasswordValid("correct horse battery staple", "correct horse battery staple")).toBe(
      true,
    );
  });

  it("rejects a different password", async () => {
    expect(await isPasswordValid("wrong", "correct")).toBe(false);
  });
});
