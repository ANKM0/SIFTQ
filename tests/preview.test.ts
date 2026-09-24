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
  it("renders the production Matrix, Ideas, and Task list with fixed scenario data", async () => {
    const matrix = await previewRequest("/");
    const ideas = await previewRequest("/ideas");
    const ideasDnd = await previewRequest("/ideas-dnd.js");
    const ideaDetail = await previewRequest("/ideas/1");
    const ideaDetailScript = await previewRequest("/idea-detail.js");
    const list = await previewRequest("/tasks?status=done");

    expect(matrix.status).toBe(200);
    const matrixBody = await matrix.text();
    expect(matrixBody).toContain("Matrix のタスクカードを見直す");
    expect(matrixBody).toContain("working");
    expect(ideas.status).toBe(200);
    const ideasBody = await ideas.text();
    expect(ideasBody).toContain("Ideas");
    expect(ideasBody).toContain("毎朝の振り返りを1分で終える");
    expect(ideasBody).toContain("資産の種類と共通点");
    expect(ideasBody).toContain('class="ideas-group-gap"');
    expect(ideasBody).toContain('draggable="true"');
    expect(ideasBody).toContain('href="/ideas/1"');
    expect(ideasBody).toContain('data-idea-modal="true"');
    expect(ideasBody).not.toContain(">Title</label>");
    expect(ideasBody).not.toContain(">Description</label>");
    expect(ideasBody.indexOf("毎朝の振り返りを1分で終える")).toBeLessThan(
      ideasBody.indexOf("あとで読みたい記事を集める"),
    );
    expect(ideasDnd.status).toBe(200);
    expect(await ideasDnd.text()).toContain("ideasSameGroup");
    expect(ideaDetail.status).toBe(200);
    const ideaDetailBody = await ideaDetail.text();
    expect(ideaDetailBody).toContain('data-idea-form="true"');
    expect(ideaDetailBody).toContain('href="/ideas"');
    expect(ideaDetailBody).toContain(">閉じる</a>");
    expect(ideaDetailBody).not.toContain("Automatically saved");
    expect(ideaDetailBody).not.toContain(">Idea</h1>");
    expect(ideaDetailScript.status).toBe(200);
    const ideaDetailScriptBody = await ideaDetailScript.text();
    expect(ideaDetailScriptBody).toContain("saveIdeaDraft");
    expect(ideaDetailScriptBody).toContain("openIdeaModal");
    expect(list.status).toBe(200);
    const listBody = await list.text();
    expect(listBody).toContain("完了したタスクの表示を確認する");
    expect(listBody).toContain("working");
  });
});
