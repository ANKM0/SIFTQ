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

function MatrixPage({ tasks }: { tasks: readonly Task[] }) {
  const matrixTasks = sortForMatrix(tasks);
  return (
    <>
      <h1>Matrix</h1>
      <a
        href="/tasks/new"
        hx-get="/tasks/new"
        hx-target="#page"
        hx-swap="innerHTML"
        hx-push-url="true"
      >
        New task
      </a>
      <div class="matrix">
        {TASK_AREAS.map((area) => (
          <section class="matrix-area" data-area={area}>
            <h2>Area {area}</h2>
            <div class="matrix-cards">
              {matrixTasks
                .filter((task) => task.area === area)
                .map((task) => (
                  <a
                    class="task-card"
                    href={`/tasks/${task.id}`}
                    hx-get={`/tasks/${task.id}`}
                    hx-target="#page"
                    hx-swap="innerHTML"
                    hx-push-url="true"
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
      <a
        href="/tasks/new"
        hx-get="/tasks/new"
        hx-target="#page"
        hx-swap="innerHTML"
        hx-push-url="true"
      >
        New task
      </a>
      <ul class="task-list">
        {tasks.map((task) => (
          <li class="task-row">
            <a
              class="task-link"
              href={`/tasks/${task.id}`}
              hx-get={`/tasks/${task.id}`}
              hx-target="#page"
              hx-swap="innerHTML"
              hx-push-url="true"
            >
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
        <label>
          Title
          <input type="text" name="title" maxlength={256} required />
        </label>
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
        <label>
          Title
          <input
            type="text"
            name="title"
            value={task.title}
            maxlength={256}
            required
          />
        </label>
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

function StatusMenu({ task }: { task: Task }) {
  return (
    <aside id="task-meta">
      <p class="menu-title">Change status</p>
      {TASK_STATUSES.map((status) => (
        <button
          class="menu-option"
          type="button"
          hx-post={`/tasks/${task.id}/status`}
          hx-vals={JSON.stringify({ status })}
          hx-target="#task-meta"
          hx-swap="innerHTML"
        >
          {status}
        </button>
      ))}
      <a
        href={`/tasks/${task.id}`}
        hx-get={`/tasks/${task.id}`}
        hx-target="#page"
        hx-swap="innerHTML"
        hx-push-url="true"
      >
        Cancel
      </a>
    </aside>
  );
}

function AreaMenu({ task }: { task: Task }) {
  return (
    <aside id="task-meta">
      <p class="menu-title">Change area</p>
      {TASK_AREAS.map((area) => (
        <button
          class="menu-option"
          type="button"
          hx-post={`/tasks/${task.id}/area`}
          hx-vals={JSON.stringify({ area })}
          hx-target="#task-meta"
          hx-swap="innerHTML"
        >
          {area}
        </button>
      ))}
      <a
        href={`/tasks/${task.id}`}
        hx-get={`/tasks/${task.id}`}
        hx-target="#page"
        hx-swap="innerHTML"
        hx-push-url="true"
      >
        Cancel
      </a>
    </aside>
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
  const body = await c.req.parseBody();
  const title = typeof body["title"] === "string" ? body["title"].trim() : "";
  const description =
    typeof body["description"] === "string" ? body["description"] : "";
  if (title === "" || title.length > 256) {
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
  const body = await c.req.parseBody();
  const title = typeof body["title"] === "string" ? body["title"].trim() : "";
  const description =
    typeof body["description"] === "string" ? body["description"] : "";
  if (title === "" || title.length > 256) {
    return c.html(
      <DetailPage
        task={task}
        error="Title is required and must be 256 characters or fewer."
      />
    );
  }
  const updated = updateTask(task, { title, description });
  const index = store.indexOf(task);
  store[index] = updated;
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
  const index = store.indexOf(task);
  store[index] = updated;
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
  const index = store.indexOf(task);
  store[index] = updated;
  return c.html(<TaskMeta task={updated} />);
});

export default app;
