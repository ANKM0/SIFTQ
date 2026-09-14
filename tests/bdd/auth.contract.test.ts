import { describe, expect, it } from "vite-plus/test";
import app from "../../src/index";
import { SESSION_COOKIE_NAME } from "../../src/auth";
import { TEST_PASSWORD, authBindings } from "../helpers/authenticated-request";
import { createMemoryTaskRepository } from "../helpers/memory-task-repository";
import type { TaskRepository } from "../../src/task-repository";

function loginRequest(repo: TaskRepository, body: string) {
  return app.request(
    "/login",
    {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body,
    },
    authBindings(repo),
  );
}

describe("authentication contract", () => {
  it("redirects unauthenticated HTML to /login", async () => {
    const response = await app.request("/", undefined, authBindings(createMemoryTaskRepository()));

    expect(response.status).toBe(302);
    expect(response.headers.get("location")).toBe("/login");
  });

  it("returns 401 for unauthenticated JSON API", async () => {
    const response = await app.request(
      "/api/tasks",
      undefined,
      authBindings(createMemoryTaskRepository()),
    );

    expect(response.status).toBe(401);
    expect((await response.json()).code).toBe("UNAUTHORIZED");
  });

  it("issues an HttpOnly session cookie after a successful login", async () => {
    const response = await loginRequest(
      createMemoryTaskRepository(),
      `password=${TEST_PASSWORD}`,
    );

    expect(response.status).toBe(302);
    expect(response.headers.get("location")).toBe("/");
    expect(response.headers.get("set-cookie")).toContain(`${SESSION_COOKIE_NAME}=`);
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
  });

  it("does not issue a session cookie after a failed login", async () => {
    const response = await loginRequest(createMemoryTaskRepository(), "password=wrong");

    expect(response.status).toBe(401);
    expect(response.headers.get("set-cookie")).toBeNull();
  });

  it("clears the session cookie on logout", async () => {
    const login = await loginRequest(
      createMemoryTaskRepository(),
      `password=${TEST_PASSWORD}&next=%2Ftasks`,
    );
    const cookie = login.headers.get("set-cookie")?.split(";")[0];
    const headers: Record<string, string> = {};
    if (cookie !== undefined) headers["Cookie"] = cookie;

    const response = await app.request(
      "/logout",
      {
        method: "POST",
        headers,
      },
      authBindings(createMemoryTaskRepository()),
    );

    expect(response.status).toBe(302);
    expect(response.headers.get("location")).toBe("/login");
    expect(response.headers.get("set-cookie")).toContain(`${SESSION_COOKIE_NAME}=`);
  });
});
