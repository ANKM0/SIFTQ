import { Hono } from "hono";
import type { Context } from "hono";
import { getCookie } from "hono/cookie";
import type { JSX } from "hono/jsx/jsx-runtime";
import type { D1Database } from "@cloudflare/workers-types";
import {
  changeTaskArea,
  changeTaskStatus,
  changeTaskWorking,
  createTask,
  isTaskStatus,
  is_working,
} from "./task";
import {
  TASK_LIST_PAGE_SIZE,
  TASK_STATUS_FILTERS,
  filterTasks,
  paginateTasks,
  parsePageParam,
  parseTaskListQuery,
} from "./task-list";
import type { TaskListQuery } from "./task-list";
import type { Task, TaskStatus } from "./task";
import {
  HTMX_CONFLICT_SWAP_SCRIPT,
  Layout,
  MATRIX_DND_SCRIPT,
  POPOVER_DISMISS_SCRIPT,
  DESCRIPTION_EDITOR_SCRIPT,
  TASK_LIST_SELECTION_SCRIPT,
  TASK_FORM_SHORTCUT_SCRIPT,
} from "./components/Layout";
import { TaskMeta } from "./components/TaskMeta";
import { OptionMenu } from "./components/OptionMenu";
import type { NewTaskFrom, NewTaskState } from "./components/NewTaskMeta";
import {
  SESSION_COOKIE_NAME,
  isValidSession,
} from "./auth";
import { createD1TaskRepository } from "./repository/d1-task-repository";
import type { TaskRepository } from "./repository/task-repository";
import { STYLES_CSS } from "./styles";
import { createMemoryTaskRepository } from "./preview/MemoryTaskRepository";
import { PREVIEW_TASKS } from "./preview/tasks";
import {
  isInvalidTaskTitle,
  parseTaskArea,
  parseTaskVersion,
  readTaskFields,
} from "./task-input";
import type { ParsedBody } from "./task-input";
import { MatrixPage } from "./views/MatrixPage";
import { pageNav } from "./views/navigation";
import { TaskListPage } from "./views/TaskListPage";
import { NewTaskForm, TaskDetailPage, TaskVersionInput } from "./views/TaskFormPage";
import { registerAuthRoutes } from "./routes/auth";
import { registerTaskApiRoutes } from "./routes/task-api";

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
  if (auth === null) {
    return c.text("Authentication is not configured", 503);
  }

  const session = getCookie(c, SESSION_COOKIE_NAME);
  if (session !== undefined && (await isValidSession(auth.secret, session))) {
    return next();
  }

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

function createTaskAtBoundary({
  title,
  description,
  status,
  area,
}: {
  title: string;
  description: string;
  status?: TaskStatus;
  area?: Task["area"];
}) {
  const now = new Date().toISOString();
  return createTask({
    id: crypto.randomUUID(),
    owner_id: "local",
    title,
    description,
    ...(status === undefined ? {} : { status }),
    ...(area === undefined ? {} : { area }),
    created_at: now,
    updated_at: now,
  });
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

function redirectAfterTaskSave(c: Context<AppEnv>, path: string): Response {
  if (c.req.header("HX-Request")) {
    c.header("HX-Redirect", path);
    return c.body(null);
  }
  return c.redirect(path);
}

async function readTaskUpdateInput(c: Context<AppEnv>) {
  const body = await c.req.parseBody();
  return {
    ...readTaskFields(body),
    version: parseTaskVersion(body["version"]),
  };
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

app.get("/task-form-shortcut.js", (c) => {
  return c.body(TASK_FORM_SHORTCUT_SCRIPT, 200, {
    "content-type": "application/javascript",
  });
});

app.get("/description-editor.js", (c) => {
  return c.body(DESCRIPTION_EDITOR_SCRIPT, 200, {
    "content-type": "application/javascript",
  });
});

app.get("/task-list-selection.js", (c) => {
  return c.body(TASK_LIST_SELECTION_SCRIPT, 200, {
    "content-type": "application/javascript",
  });
});

app.get("/styles.css", (c) => {
  return c.body(STYLES_CSS, 200, { "content-type": "text/css" });
});

app.get("/tasks", async (c) => {
  const result = await repository(c).list();
  if (!result.ok) return c.text("Internal Server Error", 500);
  const rawStatus = c.req.query("status");
  const rawQuery = c.req.query("q");
  const parsedQuery: TaskListQuery | null = parseTaskListQuery(rawQuery);
  let status: TaskStatus = "do";
  if (parsedQuery !== null) {
    status = parsedQuery.status;
  } else if (isTaskStatus(rawStatus)) {
    status = rawStatus;
  }
  let workingOnly = c.req.query("working") === "only";
  if (parsedQuery !== null) workingOnly = parsedQuery.workingOnly;
  let query = `is:${status}`;
  if (workingOnly) query += " label:working";
  if (parsedQuery !== null && rawQuery !== undefined) query = rawQuery.trim();
  const filteredTasks = filterTasks(result.value, [
    TASK_STATUS_FILTERS[status],
    ...(workingOnly ? [is_working] : []),
  ]);
  const requestedPage = parsePageParam(c.req.query("page")) ?? 1;
  const { pageTasks, currentPage, totalPages } = paginateTasks(filteredTasks, requestedPage);
  return renderPage(
    c,
    <TaskListPage
      tasks={pageTasks}
      status={status}
      workingOnly={workingOnly}
      query={query}
      currentPage={currentPage}
      totalPages={totalPages}
      pageOffset={(currentPage - 1) * TASK_LIST_PAGE_SIZE}
      queryInUrl={rawQuery}
    />,
  );
});

app.get("/tasks/new", (c) => renderPage(c, <NewTaskForm state={parseNewTaskState(c)} />));

app.get("/tasks/:id", async (c) => {
  const task = await findTask(c, c.req.param("id"));
  if (!task) return c.notFound();
  return renderPage(c, <TaskDetailPage task={task} returnTo={detailReturnTo(c)} />);
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

  const created = createTaskAtBoundary({
    title,
    description,
    status: state.status,
    area: state.area,
  });
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
      <TaskDetailPage
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

app.post("/tasks/:id/working", async (c) => {
  const task = await findTask(c, c.req.param("id"));
  if (!task) return c.notFound();

  const body = await c.req.parseBody();
  const rawWorking = body["working"];
  const version = parseTaskVersion(body["version"]);
  if ((rawWorking !== "true" && rawWorking !== "false") || version === null) {
    return c.text("Invalid working", 400);
  }

  const changed = changeTaskWorking(task, rawWorking === "true");
  if (!changed.ok) return c.text("Invalid working", 400);
  return persistTaskMeta(c, task, { ...changed.value, version }, detailReturnTo(c));
});

export default app;
