import { Hono } from "hono";
import type { Context } from "hono";
import { getCookie } from "hono/cookie";
import {
  HTMX_CONFLICT_SWAP_SCRIPT,
  MATRIX_DND_SCRIPT,
  POPOVER_DISMISS_SCRIPT,
  DESCRIPTION_EDITOR_SCRIPT,
  TASK_LIST_SELECTION_SCRIPT,
  TASK_FORM_SHORTCUT_SCRIPT,
} from "./client/browser-scripts";
import { SESSION_COOKIE_NAME, isValidSession } from "./auth";
import { createD1TaskRepository } from "./repository/d1-task-repository";
import type { TaskRepository } from "./repository/task-repository";
import { STYLES_CSS } from "./styles";
import { createMemoryTaskRepository } from "./preview/MemoryTaskRepository";
import { PREVIEW_TASKS } from "./preview/tasks";
import { registerAuthRoutes } from "./routes/auth";
import { registerTaskApiRoutes } from "./routes/task-api";
import { registerTaskScreenRoutes } from "./routes/task-screens";
import type { AppEnv } from "./app-env";

const app = new Hono<AppEnv>();
const previewRepository = createMemoryTaskRepository(PREVIEW_TASKS);

const PUBLIC_PATHS = new Set([
  "/login",
  "/styles.css",
  "/htmx-conflict.js",
  "/popover-dismiss.js",
  "/task-form-shortcut.js",
  "/matrix-dnd.js",
  "/task-list-selection.js",
]);

function isPublicPath(path: string): boolean {
  return PUBLIC_PATHS.has(path);
}

function authConfig(c: Context<AppEnv>): { password: string; secret: string } | null {
  const password = c.env.AUTH_PASSWORD;
  const secret = c.env.SESSION_SECRET;
  if (password === undefined || secret === undefined) return null;
  return { password, secret };
}

function unauthorizedResponse(c: Context<AppEnv>): Response {
  if (c.req.path.startsWith("/api/")) {
    return c.json(
      {
        type: "about:blank",
        title: "Unauthorized",
        status: 401,
        code: "UNAUTHORIZED",
      },
      401,
    );
  }
  if (c.req.header("HX-Request") === "true") {
    c.header("HX-Redirect", "/login");
    return c.body(null, 401);
  }
  return c.redirect("/login");
}

app.use("*", async (c, next) => {
  if (isPublicPath(c.req.path)) return next();
  const auth = authConfig(c);
  if (auth === null) return c.text("Authentication is not configured", 503);
  const session = getCookie(c, SESSION_COOKIE_NAME);
  if (session !== undefined && (await isValidSession(auth.secret, session))) return next();
  return unauthorizedResponse(c);
});

registerAuthRoutes(app);

function repository(c: Context<AppEnv>): TaskRepository {
  if (c.env.PREVIEW_MODE === "true") return previewRepository;
  if (c.env.TASK_REPOSITORY) return c.env.TASK_REPOSITORY;
  if (c.env.DB) return createD1TaskRepository(c.env.DB);
  throw new Error("task repository is not configured");
}

registerTaskApiRoutes(app, repository);
registerTaskScreenRoutes(app, repository);

app.get("/matrix-dnd.js", (c) => {
  return c.body(MATRIX_DND_SCRIPT, 200, { "content-type": "application/javascript" });
});

app.get("/htmx-conflict.js", (c) => {
  return c.body(HTMX_CONFLICT_SWAP_SCRIPT, 200, { "content-type": "application/javascript" });
});

app.get("/popover-dismiss.js", (c) => {
  return c.body(POPOVER_DISMISS_SCRIPT, 200, { "content-type": "application/javascript" });
});

app.get("/task-form-shortcut.js", (c) => {
  return c.body(TASK_FORM_SHORTCUT_SCRIPT, 200, { "content-type": "application/javascript" });
});

app.get("/description-editor.js", (c) => {
  return c.body(DESCRIPTION_EDITOR_SCRIPT, 200, { "content-type": "application/javascript" });
});

app.get("/task-list-selection.js", (c) => {
  return c.body(TASK_LIST_SELECTION_SCRIPT, 200, { "content-type": "application/javascript" });
});

app.get("/styles.css", (c) => c.body(STYLES_CSS, 200, { "content-type": "text/css" }));

export default app;
