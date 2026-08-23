import { Hono } from "hono";
import type { Context } from "hono";
import type { FC } from "hono/jsx";
import type { JSX } from "hono/jsx/jsx-runtime";
import type { D1Database } from "@cloudflare/workers-types";
import {
  TASK_AREAS,
  TASK_STATUSES,
  changeTaskArea,
  changeTaskStatus,
  createTask,
  isTaskArea,
  isTaskStatus,
  moveTask,
  sortForMatrix,
  updateTask,
} from "./task";
import type { Task, TaskArea } from "./task";
import { D1TaskRepository } from "./task-repository";
import type { TaskRepository } from "./task-repository";

const HTMX_SCRIPT =
  "https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js";
const SORTABLE_SCRIPT =
  "https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js";
const MATRIX_DND_SCRIPT = [
  "function initMatrixSortable() {",
  '  var lists = document.querySelectorAll(".matrix-cards[data-sortable-group]");',
  '  if (typeof Sortable === "undefined") return;',
  '  lists.forEach(function (list) {',
  "    if (Sortable.get(list)) return;",
  '    Sortable.create(list, {',
  '      group: "matrix",',
  "      animation: 150,",
  '      onEnd: function (evt) {',
  "        var card = evt.item;",
  "        var target = evt.to;",
  '        var taskId = card.getAttribute("data-task-id");',
  '        var version = card.getAttribute("data-version");',
  '        var area = target.getAttribute("data-area");',
  "        if (!taskId || !version || area === null) return;",
  '        fetch("/tasks/" + encodeURIComponent(taskId) + "/move", {',
  '          method: "POST",',
  '          headers: { "Content-Type": "application/x-www-form-urlencoded" },',
  '          body: "area=" + encodeURIComponent(area) + "&order=" + encodeURIComponent(String(evt.newIndex)) + "&version=" + encodeURIComponent(version)',
        "        }).then(function (response) {",
        "          if (!response.ok) { window.location.reload(); return null; }",
        "          return response.text();",
        "        }).then(function (html) {",
        "          if (html === null) return;",
        '          var parser = new DOMParser();',
        '          var doc = parser.parseFromString(html, "text/html");',
        '          doc.querySelectorAll(".task-card").forEach(function (fresh) {',
        '            var id = fresh.getAttribute("data-task-id");',
        '            var nextVersion = fresh.getAttribute("data-version");',
        '            if (!id || !nextVersion) return;',
        '            var cards = document.querySelectorAll(".task-card");',
        '            for (var i = 0; i < cards.length; i += 1) {',
        '              if (cards[i].getAttribute("data-task-id") === id) {',
        '                cards[i].setAttribute("data-version", nextVersion);',
        '                break;',
        '              }',
        '            }',
        "          });",
        "        }).catch(function () { window.location.reload(); });",
  "      }",
  "    });",
  "  });",
  "}",
  'document.addEventListener("DOMContentLoaded", initMatrixSortable);',
  'document.addEventListener("htmx:load", initMatrixSortable);',
].join("\n");

type Env = {
  DB?: D1Database;
  TASK_REPOSITORY?: TaskRepository;
};

type AppEnv = {
  Bindings: Env;
};

function taskRepository(c: Context<AppEnv>): TaskRepository {
  if (c.env.TASK_REPOSITORY) return c.env.TASK_REPOSITORY;
  if (!c.env.DB) throw new Error("D1 binding is not configured");
  return new D1TaskRepository(c.env.DB);
}

async function findTask(
  c: Context<AppEnv>,
  id: string,
): Promise<Task | undefined> {
  return taskRepository(c).find(id);
}

async function persistTask(
  c: Context<AppEnv>,
  updated: Task,
): Promise<Task | null> {
  const result = await taskRepository(c).update(updated);
  return result === "conflict" ? null : result;
}

async function conflictResponse(
  c: Context<AppEnv>,
  taskId: string,
): Promise<Response> {
  return await c.html(<ConflictPage taskId={taskId} />, 409);
}

async function persistTaskMeta(
  c: Context<AppEnv>,
  task: Task,
  updated: Task,
): Promise<Response> {
  const saved = await persistTask(c, updated);
  if (saved === null) return await conflictResponse(c, task.id);
  return await c.html(<TaskMeta task={saved} />);
}

const Layout: FC = ({ children }) => (
  <html lang="ja">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>SIFTQ</title>
      <script src={HTMX_SCRIPT} defer></script>
      <script src={SORTABLE_SCRIPT} defer></script>
      <script dangerouslySetInnerHTML={{ __html: MATRIX_DND_SCRIPT }}></script>
    </head>
    <body>
      <main id="page">{children}</main>
    </body>
  </html>
);

function render(c: Context, content: JSX.Element) {
  if (c.req.header("HX-Request")) {
    return c.html(content);
  }
  return c.html(<Layout>{content}</Layout>);
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

function NewTaskLink() {
  return <a {...pageNav("/tasks/new")}>New task</a>;
}

function TitleField({ value }: { value?: string }) {
  return (
    <label>
      Title
      <input type="text" name="title" value={value} maxlength={256} required />
    </label>
  );
}

type ParsedBody = Record<string, unknown>;

function readTaskFields(body: ParsedBody): {
  title: string;
  description: string;
} {
  const title = typeof body["title"] === "string" ? body["title"].trim() : "";
  const description =
    typeof body["description"] === "string" ? body["description"] : "";
  return { title, description };
}

async function readTaskInput(c: Context) {
  const body = await c.req.parseBody();
  return readTaskFields(body);
}

async function readTaskUpdateInput(c: Context) {
  const body = await c.req.parseBody();
  return {
    ...readTaskFields(body),
    version: parseTaskVersion(body["version"]),
  };
}

function isInvalidTaskTitle(title: string): boolean {
  return title === "" || title.length > 256;
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

function parseTaskArea(value: unknown): TaskArea | null {
  const area = parseTaskOrder(value);
  return area !== null && isTaskArea(area) ? area : null;
}

function MatrixPage({ tasks }: { tasks: readonly Task[] }) {
  const matrixTasks = sortForMatrix(tasks);
  return (
    <>
      <h1>Matrix</h1>
      <NewTaskLink />
      <div class="matrix">
        {TASK_AREAS.map((area) => (
          <section class="matrix-area" data-area={area}>
            <h2>Area {area}</h2>
            <div
              class="matrix-cards"
              data-area={area}
              data-sortable-group="matrix"
            >
              {matrixTasks
                .filter((task) => task.area === area)
                .map((task) => (
                  <a
                    class="task-card"
                    data-task-id={task.id}
                    data-version={task.version}
                    {...pageNav(`/tasks/${task.id}`)}
                  >
                    {task.title}
                  </a>
                ))}
            </div>
          </section>
        ))}
      </div>
    </>
  );
}

function ListPage({ tasks }: { tasks: readonly Task[] }) {
  return (
    <>
      <h1>Tasks</h1>
      <NewTaskLink />
      <ul class="task-list">
        {tasks.map((task) => (
          <li class="task-row">
            <a class="task-link" {...pageNav(`/tasks/${task.id}`)}>
              <span class="task-id">{task.id}</span>
              <span class="task-title">{task.title}</span>
              <span class="task-area">Area {task.area}</span>
              <span class="task-status">{task.status}</span>
            </a>
          </li>
        ))}
      </ul>
    </>
  );
}

function NewTaskForm({ error }: { error?: string }) {
  return (
    <>
      <h1>New task</h1>
      <form hx-post="/tasks" hx-target="#page" hx-swap="innerHTML">
        <TitleField />
        {error ? <p class="error">{error}</p> : null}
        <label>
          Description
          <textarea name="description"></textarea>
        </label>
        <button type="submit">Create</button>
      </form>
    </>
  );
}

function TaskMeta({ task }: { task: Task }) {
  return (
    <aside id="task-meta">
      <dl>
        <div class="meta-row">
          <dt>Status</dt>
          <dd>
            <span class="status-badge">{task.status}</span>
            <a
              href={`/tasks/${task.id}/status/menu`}
              hx-get={`/tasks/${task.id}/status/menu`}
              hx-target="#task-meta"
              hx-swap="innerHTML"
            >
              change
            </a>
          </dd>
        </div>
        <div class="meta-row">
          <dt>Area</dt>
          <dd>
            <span class="area-badge">{task.area}</span>
            <a
              href={`/tasks/${task.id}/area/menu`}
              hx-get={`/tasks/${task.id}/area/menu`}
              hx-target="#task-meta"
              hx-swap="innerHTML"
            >
              change
            </a>
          </dd>
        </div>
      </dl>
    </aside>
  );
}

function DetailPage({ task, error }: { task: Task; error?: string }) {
  return (
    <>
      <h1>{task.title}</h1>
      <form hx-post={`/tasks/${task.id}`} hx-target="#page" hx-swap="innerHTML">
        <TitleField value={task.title} />
        <input type="hidden" name="version" value={task.version} />
        {error ? <p class="error">{error}</p> : null}
        <label>
          Description
          <textarea name="description">{task.description}</textarea>
        </label>
        <button type="submit">Save</button>
      </form>
      <TaskMeta task={task} />
    </>
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

function OptionMenu({
  title,
  values,
  postPath,
  valueKey,
  cancelPath,
  version,
}: {
  title: string;
  values: readonly (string | number)[];
  postPath: string;
  valueKey: string;
  cancelPath: string;
  version: number;
}) {
  return (
    <aside id="task-meta">
      <p class="menu-title">{title}</p>
      {values.map((value) => (
        <button
          class="menu-option"
          type="button"
          hx-post={postPath}
          hx-vals={JSON.stringify({ [valueKey]: value, version })}
          hx-target="#task-meta"
          hx-swap="innerHTML"
        >
          {value}
        </button>
      ))}
      <a {...pageNav(cancelPath)}>Cancel</a>
    </aside>
  );
}

function StatusMenu({ task }: { task: Task }) {
  return (
    <OptionMenu
      title="Change status"
      values={TASK_STATUSES}
      postPath={`/tasks/${task.id}/status`}
      valueKey="status"
      cancelPath={`/tasks/${task.id}`}
      version={task.version}
    />
  );
}

function AreaMenu({ task }: { task: Task }) {
  return (
    <OptionMenu
      title="Change area"
      values={TASK_AREAS}
      postPath={`/tasks/${task.id}/area`}
      valueKey="area"
      cancelPath={`/tasks/${task.id}`}
      version={task.version}
    />
  );
}

const app = new Hono<AppEnv>();

app.get("/", async (c) => {
  const tasks = await taskRepository(c).list();
  return render(c, <MatrixPage tasks={tasks} />);
});

app.get("/tasks", async (c) => {
  const tasks = await taskRepository(c).list();
  return render(c, <ListPage tasks={tasks} />);
});

app.get("/tasks/new", (c) => render(c, <NewTaskForm />));

app.get("/tasks/:id", async (c) => {
  const task = await findTask(c, c.req.param("id"));
  if (!task) return c.notFound();
  return render(c, <DetailPage task={task} />);
});

app.get("/tasks/:id/status/menu", async (c) => {
  const task = await findTask(c, c.req.param("id"));
  if (!task) return c.notFound();
  return c.html(<StatusMenu task={task} />);
});

app.get("/tasks/:id/area/menu", async (c) => {
  const task = await findTask(c, c.req.param("id"));
  if (!task) return c.notFound();
  return c.html(<AreaMenu task={task} />);
});

app.post("/tasks", async (c) => {
  const { title, description } = await readTaskInput(c);
  if (isInvalidTaskTitle(title)) {
    return c.html(
      <NewTaskForm error="Title is required and must be 256 characters or fewer." />
    );
  }
  const task = createTask({ title, description });
  const created = await taskRepository(c).insert(task);
  return c.html(<DetailPage task={created} />, 201, {
    "HX-Push-Url": `/tasks/${task.id}`,
  });
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
      />
    );
  }
  const updated = { ...updateTask(task, { title, description }), version };
  const saved = await persistTask(c, updated);
  if (saved === null) return conflictResponse(c, task.id);
  return c.html(<DetailPage task={saved} />);
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
  const updated = { ...changeTaskStatus(task, status), version };
  return persistTaskMeta(c, task, updated);
});

app.post("/tasks/:id/area", async (c) => {
  const task = await findTask(c, c.req.param("id"));
  if (!task) return c.notFound();
  const body = await c.req.parseBody();
  const area = parseTaskArea(body["area"]);
  const version = parseTaskVersion(body["version"]);
  if (area === null || version === null) return c.text("Invalid area", 400);
  const updated = { ...changeTaskArea(task, area), version };
  return persistTaskMeta(c, task, updated);
});

app.post("/tasks/:id/move", async (c) => {
  const id = c.req.param("id");
  const task = await findTask(c, id);
  if (!task) return c.notFound();
  const body = await c.req.parseBody();
  const area = parseTaskArea(body["area"]);
  const order = parseTaskOrder(body["order"]);
  const version = parseTaskVersion(body["version"]);
  if (area === null || order === null || version === null) {
    return c.text("Invalid move input", 400);
  }
  if (task.version !== version) {
    return conflictResponse(c, task.id);
  }

  const repo = taskRepository(c);
  const tasks = await repo.list();
  const current = tasks.find((candidate) => candidate.id === task.id);
  if (!current || current.version !== version) {
    return conflictResponse(c, task.id);
  }
  const movedTasks = moveTask(tasks, current.id, area, order);
  const changed = movedTasks.filter((moved) => {
    const before = tasks.find((candidate) => candidate.id === moved.id);
    return (
      before !== undefined &&
      (before.area !== moved.area || before.order !== moved.order)
    );
  });
  const result = await repo.move(changed);
  if (result === "conflict") {
    return conflictResponse(c, task.id);
  }
  const versions = new Map(result.map((moved) => [moved.id, moved.version]));
  const renderedTasks = movedTasks.map((moved) => {
    const version = versions.get(moved.id);
    return version === undefined ? moved : { ...moved, version };
  });
  return c.html(<MatrixPage tasks={renderedTasks} />);
});

export default app;
