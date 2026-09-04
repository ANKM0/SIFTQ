import { Hono } from "hono";
import type { Context } from "hono";
import { deleteCookie, getCookie, setCookie } from "hono/cookie";
import type { JSX } from "hono/jsx/jsx-runtime";
import type { ContentfulStatusCode } from "hono/utils/http-status";
import type { D1Database } from "@cloudflare/workers-types";
import {
  TASK_AREAS,
  changeTaskArea,
  changeTaskStatus,
  createTask,
  isTaskArea,
  isTaskStatus,
  isTaskTitleValid,
  moveTask,
  sortForMatrix,
} from "./task";
import type { Task } from "./task";
import {
  HTMX_CONFLICT_SWAP_SCRIPT,
  Layout,
  MATRIX_DND_SCRIPT,
  POPOVER_DISMISS_SCRIPT,
} from "./components/Layout";
import { TaskCard } from "./components/TaskCard";
import { TaskRow } from "./components/TaskRow";
import { TaskMeta } from "./components/TaskMeta";
import { OptionMenu } from "./components/OptionMenu";
import { NewTaskMeta } from "./components/NewTaskMeta";
import type { NewTaskFrom, NewTaskState } from "./components/NewTaskMeta";
import { LoginPage, safeNextPath } from "./components/LoginPage";
import {
  SESSION_COOKIE_NAME,
  SESSION_DURATION_MS,
  createSession,
  isPasswordValid,
  isValidSession,
} from "./auth";
import { D1TaskRepository } from "./task-repository";
import type { TaskRepository } from "./task-repository";
import { STYLES_CSS } from "./styles";
import { MemoryTaskRepository } from "./preview/MemoryTaskRepository";
import { PREVIEW_TASKS } from "./preview/tasks";

type Env = {
  TASK_REPOSITORY?: TaskRepository;
  DB?: D1Database;
  AUTH_PASSWORD?: string;
  SESSION_SECRET?: string;
  PREVIEW_MODE?: string;
};

type AppEnv = {
  Bindings: Env;
};

const app = new Hono<AppEnv>();
const previewRepository = new MemoryTaskRepository(PREVIEW_TASKS);

const PUBLIC_PATHS = new Set([
  "/login",
  "/styles.css",
  "/htmx-conflict.js",
  "/popover-dismiss.js",
  "/matrix-dnd.js",
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
  if (auth === null) {
    return c.text("Authentication is not configured", 503);
  }

  const session = getCookie(c, SESSION_COOKIE_NAME);
  if (session !== undefined && (await isValidSession(auth.secret, session))) {
    return next();
  }

  return unauthorizedResponse(c);
});

function repository(c: Context<AppEnv>): TaskRepository {
  if (c.env.PREVIEW_MODE === "true") return previewRepository;
  if (c.env.TASK_REPOSITORY) return c.env.TASK_REPOSITORY;
  if (c.env.DB) return new D1TaskRepository(c.env.DB);
  throw new Error("task repository is not configured");
}

function problem(c: Context<AppEnv>, status: ContentfulStatusCode, code: string) {
  return c.json({ code }, status);
}

function parseVersion(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1) {
    return null;
  }
  return value;
}

function applyPatch(
  body: Record<string, unknown>,
  task: Task,
): { ok: true; task: Task } | { ok: false; code: string } {
  const withTitle = applyTitle(body, task);
  if (!withTitle) return { ok: false, code: "INVALID_TITLE" };

  const withStatus = applyStatus(body, withTitle);
  if (!withStatus) return { ok: false, code: "INVALID_STATUS" };

  const withArea = applyArea(body, withStatus);
  if (!withArea) return { ok: false, code: "INVALID_AREA" };

  return { ok: true, task: withArea };
}

function applyTitle(body: Record<string, unknown>, task: Task): Task | null {
  if (typeof body["title"] !== "string" && typeof body["description"] !== "string") {
    return task;
  }

  const title = typeof body["title"] === "string" ? body["title"].trim() : task.title;
  const description =
    typeof body["description"] === "string" ? body["description"] : task.description;
  if (!isTaskTitleValid(title)) return null;
  return { ...task, title, description };
}

function applyStatus(body: Record<string, unknown>, task: Task): Task | null {
  if (!("status" in body)) return task;
  if (!isTaskStatus(body["status"])) return null;
  const changed = changeTaskStatus(task, body["status"]);
  return changed.ok ? changed.value : null;
}

function applyArea(body: Record<string, unknown>, task: Task): Task | null {
  if (!("area" in body)) return task;
  if (!isTaskArea(body["area"])) return null;
  const changed = changeTaskArea(task, body["area"]);
  return changed.ok ? changed.value : null;
}

async function findTask(c: Context<AppEnv>, id: string): Promise<Task | undefined> {
  const result = await repository(c).find(id, "local");
  return result.ok ? result.value : undefined;
}

async function persistTask(c: Context<AppEnv>, updated: Task): Promise<Task | null> {
  const result = await repository(c).update(updated);
  return result.ok ? result.value : null;
}

async function persistTaskMeta(
  c: Context<AppEnv>,
  task: Task,
  updated: Task,
  returnTo: "matrix" | "tasks",
): Promise<Response> {
  const saved = await persistTask(c, updated);
  if (saved === null) return c.html(<ConflictPage taskId={task.id} />, 409);
  return c.html(
    <>
      <TaskMeta task={saved} returnTo={returnTo} />
      <TaskVersionInput version={saved.version} outOfBand />
    </>,
  );
}

function renderPage(c: Context<AppEnv>, content: JSX.Element) {
  if (c.req.header("HX-Request")) {
    return c.html(content);
  }
  const active = c.req.path === "/" ? "matrix" : "tasks";
  return c.html(<Layout active={active}>{content}</Layout>);
}

function pageNav(path: string) {
  return {
    href: path,
    "hx-get": path,
    "hx-target": "#page",
    "hx-swap": "innerHTML",
    "hx-push-url": "true",
  };
}

function redirectAfterTaskSave(c: Context<AppEnv>, path: string): Response {
  if (c.req.header("HX-Request")) {
    c.header("HX-Redirect", path);
    return c.body(null);
  }
  return c.redirect(path);
}

function NewTaskLink({ from }: { from: NewTaskFrom }) {
  return (
    <a class="button primary" {...pageNav(`/tasks/new?from=${from}`)}>
      New task
    </a>
  );
}

function TitleField({ value }: { value?: string }) {
  return (
    <label>
      Title
      <input type="text" name="title" value={value} maxlength={256} required />
    </label>
  );
}

function DescriptionField({ children }: { children?: string }) {
  return (
    <label>
      Description
      <textarea name="description">{children}</textarea>
    </label>
  );
}

function TaskVersionInput({ version, outOfBand = false }: { version: number; outOfBand?: boolean }) {
  return (
    <input
      id="task-version"
      type="hidden"
      name="version"
      value={version}
      hx-swap-oob={outOfBand ? "true" : undefined}
    />
  );
}

function TaskFormActions({ submitLabel, cancelHref }: { submitLabel: string; cancelHref: string }) {
  return (
    <div class="form-actions">
      <a class="button" href={cancelHref}>
        Cancel
      </a>
      <button class="button primary" type="submit">
        {submitLabel}
      </button>
    </div>
  );
}

type ParsedBody = Record<string, unknown>;

function readTaskFields(body: ParsedBody): {
  title: string;
  description: string;
} {
  const title = typeof body["title"] === "string" ? body["title"].trim() : "";
  const description = typeof body["description"] === "string" ? body["description"] : "";
  return { title, description };
}

async function readTaskUpdateInput(c: Context<AppEnv>) {
  const body = await c.req.parseBody();
  return {
    ...readTaskFields(body),
    version: parseTaskVersion(body["version"]),
  };
}

function isInvalidTaskTitle(title: string): boolean {
  return !isTaskTitleValid(title);
}

function parseTaskOrder(value: unknown): number | null {
  if (typeof value !== "string" || value === "") return null;
  const order = Number(value);
  if (!Number.isInteger(order) || order < 0) return null;
  return order;
}

function parseTaskVersion(value: unknown): number | null {
  if (typeof value !== "string" || value === "") return null;
  const version = Number(value);
  if (!Number.isInteger(version) || version < 1) return null;
  return version;
}

function parseTaskArea(value: unknown): Task["area"] | null {
  const area = parseTaskOrder(value);
  return area !== null && isTaskArea(area) ? area : null;
}

function parseNewTaskState(c: Context<AppEnv>): NewTaskState {
  const status = c.req.query("status");
  const area = c.req.query("area");
  const parsedArea = parseTaskArea(area);

  return {
    status: isTaskStatus(status) ? status : "do",
    area: parsedArea ?? 1,
    from: c.req.query("from") === "matrix" ? "matrix" : "tasks",
  };
}

function detailReturnTo(c: Context<AppEnv>): "matrix" | "tasks" {
  return c.req.query("from") === "matrix" ? "matrix" : "tasks";
}

function newTaskOrigin(c: Context<AppEnv>, body: ParsedBody): NewTaskFrom {
  if (body["from"] === "matrix" || c.req.query("from") === "matrix") return "matrix";
  return "tasks";
}

function MatrixPage({ tasks }: { tasks: readonly Task[] }) {
  const matrixTasks = sortForMatrix(tasks);
  return (
    <div class="page page--matrix" data-state="normal">
      <div class="page-header">
        <div>
          <h1 class="page-title">Matrix</h1>
          <p class="muted">Organize tasks by urgency and importance.</p>
        </div>
        <NewTaskLink from="matrix" />
      </div>
      <p id="dnd-conflict" class="error" hidden>
        Task was updated elsewhere. The Matrix was restored to the latest state.
      </p>
      <div class="matrix matrix-axis" aria-label="Four status matrix">
        <div class="axis-line axis-line--horizontal" aria-hidden="true">
          <span>緊急度</span>
        </div>
        <div class="axis-line axis-line--vertical" aria-hidden="true">
          <span>重要度</span>
        </div>
        {TASK_AREAS.map((area) => (
          <section
            key={area}
            class={`area area--quadrant area--q${area}`}
            aria-labelledby={`area-${area}`}
            data-drop-area={area}
          >
            <a class="area-create-link" href={`/tasks/new?area=${area}&from=matrix`} aria-label={`Create task in area ${area}`}>
              <span aria-hidden="true"></span>
            </a>
            <h2 id={`area-${area}`}>{area}</h2>
            <div class="matrix-cards" data-area={area} data-dnd-group="matrix">
              {matrixTasks
                .filter((task) => task.area === area)
                .map((task) => (
                  <TaskCard key={task.id} task={task} />
                ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function ListPage({ tasks }: { tasks: readonly Task[] }) {
  return (
    <div class="page page--list" data-state="normal">
      <div class="page-header">
        <div>
          <h1 class="page-title">Tasks</h1>
          <p class="muted">GitHub Issues-like list without search in this scope.</p>
        </div>
        <NewTaskLink from="tasks" />
      </div>
      <div class="list" aria-label="Task list">
        {tasks.map((task, index) => (
          <TaskRow key={task.id} task={task} issueNumber={index + 1} />
        ))}
      </div>
    </div>
  );
}

function NewTaskForm({ state, error }: { state: NewTaskState; error?: string }) {
  return (
    <div class="page page--new" data-state="normal">
      <div class="page-header">
        <h1 class="page-title">New task</h1>
      </div>
      <form class="detail-grid" hx-post="/tasks" hx-target="#page" hx-swap="innerHTML">
        <div class="form-panel">
          <TitleField />
          <input type="hidden" name="from" value={state.from} />
          {error ? <p class="error">{error}</p> : null}
          <DescriptionField />
          <TaskFormActions submitLabel="Create" cancelHref={state.from === "matrix" ? "/" : "/tasks"} />
        </div>
        <NewTaskMeta state={state} />
      </form>
    </div>
  );
}

function DetailPage({
  task,
  error,
  returnTo = "tasks",
}: {
  task: Task;
  error?: string;
  returnTo?: "matrix" | "tasks";
}) {
  const cancelHref = returnTo === "matrix" ? "/" : "/tasks";

  return (
    <div class="page page--detail" data-state="normal">
      <div class="page-header">
        <h1 class="page-title">Task detail</h1>
        <a class="button" href={cancelHref}>
          Tasks
        </a>
      </div>
      <div class="detail-grid">
        <form
          class="form-panel"
          method="post"
          action={`/tasks/${task.id}?from=${returnTo}`}
          hx-post={`/tasks/${task.id}?from=${returnTo}`}
          hx-target="#page"
          hx-swap="innerHTML"
        >
          <TitleField value={task.title} />
          <TaskVersionInput version={task.version} />
          {error ? <p class="error">{error}</p> : null}
          <DescriptionField>{task.description}</DescriptionField>
          <TaskFormActions submitLabel="Save" cancelHref={cancelHref} />
        </form>
        <TaskMeta task={task} returnTo={returnTo} />
      </div>
    </div>
  );
}

function ConflictPage({ taskId }: { taskId: string }) {
  return (
    <div class="error">
      <p>Task was updated elsewhere.</p>
      <a {...pageNav(`/tasks/${taskId}`)}>Load latest</a>
    </div>
  );
}

function StatusMenu({ task, returnTo }: { task: Task; returnTo: "matrix" | "tasks" }) {
  return <OptionMenu task={task} open="status" returnTo={returnTo} />;
}

function AreaMenu({ task, returnTo }: { task: Task; returnTo: "matrix" | "tasks" }) {
  return <OptionMenu task={task} open="area" returnTo={returnTo} />;
}

app.get("/login", (c) => {
  const next = c.req.query("next");
  if (next === undefined) {
    return c.html(<LoginPage error={c.req.query("error") === "1"} />);
  }
  return c.html(<LoginPage error={c.req.query("error") === "1"} next={next} />);
});

app.post("/login", async (c) => {
  const auth = authConfig(c);
  if (auth === null) return c.text("Authentication is not configured", 503);

  const body = await c.req.parseBody();
  const password = typeof body["password"] === "string" ? body["password"] : "";
  const next = typeof body["next"] === "string" ? body["next"] : "/";

  if (!(await isPasswordValid(password, auth.password))) {
    return c.html(<LoginPage error next={next} />, 401);
  }

  const expires = Date.now() + SESSION_DURATION_MS;
  const session = await createSession(auth.secret, expires);
  setCookie(c, SESSION_COOKIE_NAME, session, {
    httpOnly: true,
    sameSite: "Lax",
    secure: true,
    path: "/",
    expires: new Date(expires),
  });
  return c.redirect(safeNextPath(next));
});

app.post("/logout", (c) => {
  deleteCookie(c, SESSION_COOKIE_NAME, { path: "/" });
  return c.redirect("/login");
});

app.get("/", async (c) => {
  const result = await repository(c).list();
  if (!result.ok) return c.text("Internal Server Error", 500);
  return renderPage(c, <MatrixPage tasks={result.value} />);
});

app.get("/matrix-dnd.js", (c) => {
  return c.body(MATRIX_DND_SCRIPT, 200, {
    "content-type": "application/javascript",
  });
});

app.get("/htmx-conflict.js", (c) => {
  return c.body(HTMX_CONFLICT_SWAP_SCRIPT, 200, {
    "content-type": "application/javascript",
  });
});

app.get("/popover-dismiss.js", (c) => {
  return c.body(POPOVER_DISMISS_SCRIPT, 200, {
    "content-type": "application/javascript",
  });
});

app.get("/styles.css", (c) => {
  return c.body(STYLES_CSS, 200, { "content-type": "text/css" });
});

app.get("/api/tasks", async (c) => {
  const result = await repository(c).list();
  if (!result.ok) return problem(c, 500, result.error.code);
  return c.json(result.value);
});

app.get("/api/tasks/:id", async (c) => {
  const result = await repository(c).find(c.req.param("id"), "local");
  if (!result.ok) return problem(c, 500, result.error.code);
  if (!result.value) return problem(c, 404, "NOT_FOUND");
  return c.json(result.value);
});

app.post("/api/tasks", async (c) => {
  const body = await c.req.json<Record<string, unknown>>();
  const title = typeof body["title"] === "string" ? body["title"].trim() : "";
  const description = typeof body["description"] === "string" ? body["description"] : "";

  if (!isTaskTitleValid(title)) {
    return problem(c, 400, "INVALID_TITLE");
  }

  const created = createTask({ owner_id: "local", title, description });
  if (!created.ok) return problem(c, 400, created.error.code);

  const inserted = await repository(c).insert(created.value);
  if (!inserted.ok) return problem(c, 500, inserted.error.code);

  c.header("Location", `/api/tasks/${inserted.value.id}`);
  return c.json(inserted.value, 201);
});

app.patch("/api/tasks/:id", async (c) => {
  const body = await c.req.json<Record<string, unknown>>();
  const found = await repository(c).find(c.req.param("id"), "local");
  if (!found.ok) return problem(c, 500, found.error.code);
  if (!found.value) return problem(c, 404, "NOT_FOUND");

  const patched = applyPatch(body, found.value);
  if (!patched.ok) return problem(c, 400, patched.code);
  const task = patched.task;

  const version = parseVersion(body["version"]);
  if (version === null) {
    return problem(c, 400, "INVALID_ORDER");
  }

  const updated = await repository(c).update({ ...task, version });
  if (!updated.ok) return problem(c, 409, updated.error.code);
  return c.json(updated.value);
});

app.post("/api/tasks/reorder", async (c) => {
  const body = await c.req.json<Record<string, unknown>>();
  const id = typeof body["id"] === "string" ? body["id"] : "";
  const version = parseVersion(body["version"]);
  const area = body["area"];
  const order = body["order"];
  if (
    !isTaskArea(area) ||
    typeof order !== "number" ||
    !Number.isInteger(order) ||
    version === null
  ) {
    return problem(c, 400, "INVALID_ORDER");
  }

  const listed = await repository(c).list();
  if (!listed.ok) return problem(c, 500, listed.error.code);

  const tasks = listed.value;
  const moved = moveTask(tasks, id, area, order);
  if (!moved.ok) return problem(c, 400, moved.error.code);

  const changed = moved.value.filter((task) => {
    const before = tasks.find((candidate) => candidate.id === task.id);
    return before !== undefined && (before.area !== task.area || before.order !== task.order);
  });
  const changedWithVersion = changed.map((task) => (task.id === id ? { ...task, version } : task));

  const result = await repository(c).move(changedWithVersion);
  if (!result.ok) return problem(c, 409, result.error.code);

  return c.json(result.value);
});

app.get("/tasks", async (c) => {
  const result = await repository(c).list();
  if (!result.ok) return c.text("Internal Server Error", 500);
  return renderPage(c, <ListPage tasks={result.value} />);
});

app.get("/tasks/new", (c) => renderPage(c, <NewTaskForm state={parseNewTaskState(c)} />));

app.get("/tasks/:id", async (c) => {
  const task = await findTask(c, c.req.param("id"));
  if (!task) return c.notFound();
  return renderPage(c, <DetailPage task={task} returnTo={detailReturnTo(c)} />);
});

app.get("/tasks/:id/status/menu", async (c) => {
  const task = await findTask(c, c.req.param("id"));
  if (!task) return c.notFound();
  return c.html(<StatusMenu task={task} returnTo={detailReturnTo(c)} />);
});

app.get("/tasks/:id/area/menu", async (c) => {
  const task = await findTask(c, c.req.param("id"));
  if (!task) return c.notFound();
  return c.html(<AreaMenu task={task} returnTo={detailReturnTo(c)} />);
});

app.post("/tasks", async (c) => {
  const body = await c.req.parseBody();
  const { title, description } = readTaskFields(body);
  const status = body["status"];
  const area = parseTaskArea(body["area"]);
  const state: NewTaskState = {
    status: isTaskStatus(status) ? status : "do",
    area: area ?? 1,
    from: newTaskOrigin(c, body),
  };
  if (isInvalidTaskTitle(title)) {
    return c.html(
      <NewTaskForm state={state} error="Title is required and must be 256 characters or fewer." />,
    );
  }

  const created = createTask({ owner_id: "local", title, description, status: state.status, area: state.area });
  if (!created.ok) return c.text("Invalid title", 400);

  const inserted = await repository(c).insert(created.value);
  if (!inserted.ok) return c.text("Internal Server Error", 500);

  c.header("HX-Redirect", state.from === "matrix" ? "/" : "/tasks");
  return c.body(null, 201);
});

app.post("/tasks/:id", async (c) => {
  const task = await findTask(c, c.req.param("id"));
  if (!task) return c.notFound();

  const { title, description, version } = await readTaskUpdateInput(c);
  if (version === null) return c.text("Invalid version", 400);
  if (isInvalidTaskTitle(title)) {
    return c.html(
      <DetailPage
        task={task}
        error="Title is required and must be 256 characters or fewer."
        returnTo={detailReturnTo(c)}
      />,
    );
  }

  const updated = { ...task, title, description, version };
  const saved = await persistTask(c, updated);
  if (saved === null) return c.html(<ConflictPage taskId={task.id} />, 409);
  return redirectAfterTaskSave(c, detailReturnTo(c) === "matrix" ? "/" : "/tasks");
});

app.post("/tasks/:id/status", async (c) => {
  const task = await findTask(c, c.req.param("id"));
  if (!task) return c.notFound();

  const body = await c.req.parseBody();
  const status = body["status"];
  const version = parseTaskVersion(body["version"]);
  if (!isTaskStatus(status) || version === null) {
    return c.text("Invalid status", 400);
  }

  const changed = changeTaskStatus(task, status);
  if (!changed.ok) return c.text("Invalid status", 400);
  return persistTaskMeta(c, task, { ...changed.value, version }, detailReturnTo(c));
});

app.post("/tasks/:id/area", async (c) => {
  const task = await findTask(c, c.req.param("id"));
  if (!task) return c.notFound();

  const body = await c.req.parseBody();
  const area = parseTaskArea(body["area"]);
  const version = parseTaskVersion(body["version"]);
  if (area === null || version === null) return c.text("Invalid area", 400);

  const changed = changeTaskArea(task, area);
  if (!changed.ok) return c.text("Invalid area", 400);
  return persistTaskMeta(c, task, { ...changed.value, version }, detailReturnTo(c));
});

export default app;
