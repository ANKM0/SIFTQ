import { Hono } from "hono";
import type { Context } from "hono";
import type { FC } from "hono/jsx";
import type { JSX } from "hono/jsx/jsx-runtime";
import {
  TASK_AREAS,
  TASK_STATUSES,
  changeTaskArea,
  changeTaskStatus,
  createTask,
  isTaskArea,
  isTaskStatus,
  seedTasks,
  sortForMatrix,
  updateTask,
} from "./task";
import type { Task } from "./task";

const HTMX_SCRIPT =
  "https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js";

const store: Task[] = seedTasks();

const Layout: FC = ({ children }) => (
  <html lang="ja">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>SIFTQ</title>
      <script src={HTMX_SCRIPT} defer></script>
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

async function readTaskInput(c: Context) {
  const body = await c.req.parseBody();
  const title = typeof body["title"] === "string" ? body["title"].trim() : "";
  const description =
    typeof body["description"] === "string" ? body["description"] : "";
  return { title, description };
}

function isInvalidTaskTitle(title: string): boolean {
  return title === "" || title.length > 256;
}

function replaceInStore(tasks: Task[], task: Task, updated: Task) {
  const index = tasks.indexOf(task);
  tasks[index] = updated;
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
            <div class="matrix-cards">
              {matrixTasks
                .filter((task) => task.area === area)
                .map((task) => (
                  <a class="task-card" {...pageNav(`/tasks/${task.id}`)}>
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

function OptionMenu({
  title,
  values,
  postPath,
  valueKey,
  cancelPath,
}: {
  title: string;
  values: readonly (string | number)[];
  postPath: string;
  valueKey: string;
  cancelPath: string;
}) {
  return (
    <aside id="task-meta">
      <p class="menu-title">{title}</p>
      {values.map((value) => (
        <button
          class="menu-option"
          type="button"
          hx-post={postPath}
          hx-vals={JSON.stringify({ [valueKey]: value })}
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
    />
  );
}

const app = new Hono();

app.get("/", (c) => render(c, <MatrixPage tasks={store} />));

app.get("/tasks", (c) => render(c, <ListPage tasks={store} />));

app.get("/tasks/new", (c) => render(c, <NewTaskForm />));

app.get("/tasks/:id", (c) => {
  const task = store.find((t) => t.id === c.req.param("id"));
  if (!task) return c.notFound();
  return render(c, <DetailPage task={task} />);
});

app.get("/tasks/:id/status/menu", (c) => {
  const task = store.find((t) => t.id === c.req.param("id"));
  if (!task) return c.notFound();
  return c.html(<StatusMenu task={task} />);
});

app.get("/tasks/:id/area/menu", (c) => {
  const task = store.find((t) => t.id === c.req.param("id"));
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
  store.push(task);
  return c.html(<DetailPage task={task} />, 201, {
    "HX-Push-Url": `/tasks/${task.id}`,
  });
});

app.post("/tasks/:id", async (c) => {
  const task = store.find((t) => t.id === c.req.param("id"));
  if (!task) return c.notFound();
  const { title, description } = await readTaskInput(c);
  if (isInvalidTaskTitle(title)) {
    return c.html(
      <DetailPage
        task={task}
        error="Title is required and must be 256 characters or fewer."
      />
    );
  }
  const updated = updateTask(task, { title, description });
  replaceInStore(store, task, updated);
  return c.html(<DetailPage task={updated} />);
});

app.post("/tasks/:id/status", async (c) => {
  const task = store.find((t) => t.id === c.req.param("id"));
  if (!task) return c.notFound();
  const body = await c.req.parseBody();
  const status = body["status"];
  if (!isTaskStatus(status)) {
    return c.html(<TaskMeta task={task} />);
  }
  const updated = changeTaskStatus(task, status);
  replaceInStore(store, task, updated);
  return c.html(<TaskMeta task={updated} />);
});

app.post("/tasks/:id/area", async (c) => {
  const task = store.find((t) => t.id === c.req.param("id"));
  if (!task) return c.notFound();
  const body = await c.req.parseBody();
  const area = Number(body["area"]);
  if (!isTaskArea(area)) {
    return c.html(<TaskMeta task={task} />);
  }
  const updated = changeTaskArea(task, area);
  replaceInStore(store, task, updated);
  return c.html(<TaskMeta task={updated} />);
});

export default app;
