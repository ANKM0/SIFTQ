import type { Context, Hono } from "hono";
import type { JSX } from "hono/jsx/jsx-runtime";
import {
  Layout,
} from "../components/Layout";
import { OptionMenu } from "../components/OptionMenu";
import { TaskMeta } from "../components/TaskMeta";
import type { NewTaskFrom, NewTaskState } from "../components/NewTaskMeta";
import { MatrixPage } from "../views/MatrixPage";
import { IdeasPage } from "../views/IdeasPage";
import { IdeaDetailPage } from "../views/IdeaDetailPage";
import { TaskListPage } from "../views/TaskListPage";
import { NewTaskForm, TaskDetailPage, TaskVersionInput } from "../views/TaskFormPage";
import { pageNav } from "../views/navigation";
import { changeTaskArea, changeTaskStatus, changeTaskWorking, createTask, isTaskStatus, is_working } from "../task";
import type { Task, TaskStatus } from "../task";
import {
  TASK_STATUS_FILTERS,
  filterTasks,
  paginateTasks,
  parsePageParam,
  parseTaskListQuery,
} from "../task-list";
import type { TaskListQuery } from "../task-list";
import {
  isInvalidTaskDescription,
  isInvalidTaskTitle,
  parseTaskArea,
  parseTaskVersion,
  readTaskFields,
} from "../task-input";
import type { ParsedBody } from "../task-input";
import type { AppEnv } from "../app-env";
import type { TaskRepository } from "../repository/task-repository";
import type { IdeaRepository } from "../repository/idea-repository";

type Repository = (c: Context<AppEnv>) => TaskRepository;
type IdeaRepositoryFactory = (c: Context<AppEnv>) => IdeaRepository;

function activePage(path: string): "ideas" | "matrix" | "tasks" {
  if (path === "/matrix") return "matrix";
  if (path === "/ideas" || path.startsWith("/ideas/")) return "ideas";
  return "tasks";
}

function renderPage(c: Context<AppEnv>, content: JSX.Element) {
  if (c.req.header("HX-Request")) return c.html(content);
  return c.html(<Layout active={activePage(c.req.path)}>{content}</Layout>);
}

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

async function findTask(c: Context<AppEnv>, repository: Repository, id: string): Promise<Task | undefined> {
  const result = await repository(c).find(id, "local");
  return result.ok ? result.value : undefined;
}

async function persistTask(c: Context<AppEnv>, repository: Repository, updated: Task): Promise<Task | null> {
  const result = await repository(c).update(updated);
  return result.ok ? result.value : null;
}

function taskTextError(title: string, description: string): string | undefined {
  if (isInvalidTaskTitle(title)) return "Title is required and must be 256 characters or fewer.";
  if (isInvalidTaskDescription(description)) return "Description must be 16,384 characters or fewer.";
  return undefined;
}

function detailReturnTo(c: Context<AppEnv>): "matrix" | "tasks" {
  return c.req.query("from") === "matrix" ? "matrix" : "tasks";
}

function detailListStatus(c: Context<AppEnv>): TaskStatus {
  const status = c.req.query("status");
  return isTaskStatus(status) ? status : "do";
}

function parseNewTaskState(c: Context<AppEnv>): NewTaskState {
  const status = c.req.query("status");
  const area = parseTaskArea(c.req.query("area"));
  return {
    status: isTaskStatus(status) ? status : "do",
    area: area ?? 1,
    from: c.req.query("from") === "matrix" ? "matrix" : "tasks",
  };
}

function newTaskOrigin(c: Context<AppEnv>, body: ParsedBody): NewTaskFrom {
  return body["from"] === "matrix" || c.req.query("from") === "matrix" ? "matrix" : "tasks";
}

function ConflictPage({ taskId }: { taskId: string }) {
  return (
    <div class="error">
      <p>Task was updated elsewhere.</p>
      <a {...pageNav(`/tasks/${taskId}`)}>Load latest</a>
    </div>
  );
}

function registerTaskListRoutes(app: Hono<AppEnv>, repository: Repository, ideaRepository: IdeaRepositoryFactory) {
  app.get("/", (c) => c.redirect("/ideas"));

  app.get("/matrix", async (c) => {
    const result = await repository(c).list();
    if (!result.ok) return c.text("Internal Server Error", 500);
    return renderPage(c, <MatrixPage tasks={result.value} />);
  });

  app.get("/ideas", async (c) => {
    const result = await ideaRepository(c).list("local");
    if (!result.ok) return c.text("Internal Server Error", 500);
    return renderPage(c, <IdeasPage ideas={result.value} />);
  });

  app.get("/ideas/:id", async (c) => {
    const result = await ideaRepository(c).find(c.req.param("id"), "local");
    if (!result.ok) return c.text("Internal Server Error", 500);
    return result.value === undefined ? c.notFound() : renderPage(c, <IdeaDetailPage idea={result.value} />);
  });

  app.get("/tasks", async (c) => {
    const result = await repository(c).list();
    if (!result.ok) return c.text("Internal Server Error", 500);
    const rawStatus = c.req.query("status");
    const rawQuery = c.req.query("q");
    const parsedQuery: TaskListQuery | null = parseTaskListQuery(rawQuery);
    let status: TaskStatus = "do";
    if (parsedQuery !== null) status = parsedQuery.status;
    else if (isTaskStatus(rawStatus)) status = rawStatus;
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
        queryInUrl={rawQuery}
      />,
    );
  });
}

function registerTaskDetailRoutes(app: Hono<AppEnv>, repository: Repository) {
  app.get("/tasks/new", (c) => renderPage(c, <NewTaskForm state={parseNewTaskState(c)} />));

  app.get("/tasks/:id", async (c) => {
    const task = await findTask(c, repository, c.req.param("id"));
    if (!task) return c.notFound();
    return renderPage(c, <TaskDetailPage task={task} returnTo={detailReturnTo(c)} listStatus={detailListStatus(c)} />);
  });

  app.get("/tasks/:id/status/menu", async (c) => {
    const task = await findTask(c, repository, c.req.param("id"));
    if (!task) return c.notFound();
    return c.html(<OptionMenu task={task} open="status" returnTo={detailReturnTo(c)} listStatus={detailListStatus(c)} />);
  });

  app.get("/tasks/:id/area/menu", async (c) => {
    const task = await findTask(c, repository, c.req.param("id"));
    if (!task) return c.notFound();
    return c.html(<OptionMenu task={task} open="area" returnTo={detailReturnTo(c)} listStatus={detailListStatus(c)} />);
  });
}

function registerTaskCreateRoute(app: Hono<AppEnv>, repository: Repository) {
  app.post("/tasks", async (c) => {
    const body = await c.req.parseBody();
    const { title, description } = readTaskFields(body);
    const state: NewTaskState = {
      status: isTaskStatus(body["status"]) ? body["status"] : "do",
      area: parseTaskArea(body["area"]) ?? 1,
      from: newTaskOrigin(c, body),
    };
    const error = taskTextError(title, description);
    if (error !== undefined) return c.html(<NewTaskForm state={state} error={error} />);
    const created = createTaskAtBoundary({ title, description, status: state.status, area: state.area });
    if (!created.ok) return c.text(`Invalid task: ${created.error.code}`, 400);
    const inserted = await repository(c).insert(created.value);
    if (!inserted.ok) return c.text("Internal Server Error", 500);
    c.header("HX-Redirect", state.from === "matrix" ? "/matrix" : "/tasks");
    return c.body(null, 201);
  });
}

function registerTaskEditRoutes(app: Hono<AppEnv>, repository: Repository) {
  app.post("/tasks/:id", async (c) => {
    const task = await findTask(c, repository, c.req.param("id"));
    if (!task) return c.notFound();
    const body = await c.req.parseBody();
    const { title, description } = readTaskFields(body);
    const version = parseTaskVersion(body["version"]);
    if (version === null) return c.text("Invalid version", 400);
    const error = taskTextError(title, description);
    if (error !== undefined) return c.html(<TaskDetailPage task={task} error={error} returnTo={detailReturnTo(c)} listStatus={detailListStatus(c)} />);
    const saved = await persistTask(c, repository, { ...task, title, description, version });
    if (saved === null) return c.html(<ConflictPage taskId={task.id} />, 409);
    const path = detailReturnTo(c) === "matrix" ? "/matrix" : "/tasks";
    if (c.req.header("HX-Request")) {
      c.header("HX-Redirect", path);
      return c.body(null);
    }
    return c.redirect(path);
  });

  app.post("/tasks/:id/status", async (c) => {
    const task = await findTask(c, repository, c.req.param("id"));
    if (!task) return c.notFound();
    const body = await c.req.parseBody();
    const status = body["status"];
    const version = parseTaskVersion(body["version"]);
    if (!isTaskStatus(status) || version === null) return c.text("Invalid status", 400);
    const changed = changeTaskStatus(task, status);
    if (!changed.ok) return c.text("Invalid status", 400);
    return updateTaskMeta(c, repository, task, { ...changed.value, version }, detailReturnTo(c), detailListStatus(c));
  });

  app.post("/tasks/:id/area", async (c) => {
    const task = await findTask(c, repository, c.req.param("id"));
    if (!task) return c.notFound();
    const body = await c.req.parseBody();
    const area = parseTaskArea(body["area"]);
    const version = parseTaskVersion(body["version"]);
    if (area === null || version === null) return c.text("Invalid area", 400);
    const changed = changeTaskArea(task, area);
    if (!changed.ok) return c.text("Invalid area", 400);
    return updateTaskMeta(c, repository, task, { ...changed.value, version }, detailReturnTo(c), detailListStatus(c));
  });

  app.post("/tasks/:id/working", async (c) => {
    const task = await findTask(c, repository, c.req.param("id"));
    if (!task) return c.notFound();
    const body = await c.req.parseBody();
    const rawWorking = body["working"];
    const version = parseTaskVersion(body["version"]);
    if ((rawWorking !== "true" && rawWorking !== "false") || version === null) return c.text("Invalid working", 400);
    const changed = changeTaskWorking(task, rawWorking === "true");
    if (!changed.ok) return c.text("Invalid working", 400);
    return updateTaskMeta(c, repository, task, { ...changed.value, version }, detailReturnTo(c), detailListStatus(c));
  });
}

export function registerTaskScreenRoutes(app: Hono<AppEnv>, repository: Repository, ideaRepository: IdeaRepositoryFactory) {
  registerTaskListRoutes(app, repository, ideaRepository);
  registerTaskDetailRoutes(app, repository);
  registerTaskCreateRoute(app, repository);
  registerTaskEditRoutes(app, repository);
}

async function updateTaskMeta(
  c: Context<AppEnv>,
  repository: Repository,
  task: Task,
  updated: Task,
  returnTo: "matrix" | "tasks",
  listStatus: TaskStatus,
) {
  const saved = await persistTask(c, repository, updated);
  if (saved === null) return c.html(<ConflictPage taskId={task.id} />, 409);
  return c.html(
    <>
      <TaskMeta task={saved} returnTo={returnTo} listStatus={listStatus} />
      <TaskVersionInput version={saved.version} outOfBand />
    </>,
  );
}
