import { describe, expect, it } from "vite-plus/test";
import app from "../src/index";
import { SESSION_COOKIE_NAME, createSession } from "../src/auth";

const PREVIEW_SECRET = "preview-session-secret";

async function previewRequest(path: string): Promise<Response> {
  const session = await createSession(PREVIEW_SECRET, Date.now() + 60_000);
  return app.request(
    path,
    { headers: { Cookie: `${SESSION_COOKIE_NAME}=${session}` } },
    {
      PREVIEW_MODE: "true",
      AUTH_PASSWORD: "preview",
      SESSION_SECRET: PREVIEW_SECRET,
    },
  );
}

describe("mock backend preview", () => {
  it("renders the production Matrix and Task list with fixed scenario data", async () => {
    const matrix = await previewRequest("/");
    const list = await previewRequest("/tasks?status=done");

    expect(matrix.status).toBe(200);
    expect(await matrix.text()).toContain("Matrix のタスクカードを見直す");
    expect(list.status).toBe(200);
    expect(await list.text()).toContain("完了したタスクの表示を確認する");
  });
});
