import type { FC } from "hono/jsx";
import type { JSX } from "hono/jsx/jsx-runtime";
import type { Task, TaskStatus } from "../task";

export const TaskMeta: FC<{ task: Task; returnTo?: "matrix" | "tasks"; listStatus?: TaskStatus }> = ({
  task,
  returnTo,
  listStatus = "do",
}) => {
  if (returnTo === undefined) return <TaskSidePanel task={task} listStatus={listStatus} />;
  return <TaskSidePanel task={task} returnTo={returnTo} listStatus={listStatus} />;
};

export const TaskSidePanel: FC<{
  task: Task;
  className?: string;
  children?: JSX.Element;
  returnTo?: "matrix" | "tasks";
  listStatus?: TaskStatus;
}> = ({
  task,
  className = "side-panel",
  children,
  returnTo = "tasks",
  listStatus = "do",
}) => {
  const statusQuery = returnTo === "matrix" ? "" : `&status=${listStatus}`;
  const detailPath = `/tasks/${task.id}?from=${returnTo}${statusQuery}`;
  const statusPath = `/tasks/${task.id}/status/menu?from=${returnTo}${statusQuery}`;
  const areaPath = `/tasks/${task.id}/area/menu?from=${returnTo}${statusQuery}`;
  const workingPath = `/tasks/${task.id}/working?from=${returnTo}${statusQuery}`;

  return (
    <aside
      id="task-meta"
      class={className}
      data-popover-close-href={children === undefined ? undefined : detailPath}
    >
      <MetaRow label="Status" path={statusPath} />
      <a
        class={`status status--${task.status}`}
        href={statusPath}
        hx-get={statusPath}
        hx-target="#task-meta"
        hx-swap="innerHTML"
      >
        {task.status}
      </a>
      <MetaRow label="Area" path={areaPath} spaced />
      <a
        class="status area-badge"
        href={areaPath}
        hx-get={areaPath}
        hx-target="#task-meta"
        hx-swap="innerHTML"
      >
        {task.area}
      </a>
      <div class="meta-row meta-row--spaced">
        <h2>Working</h2>
      </div>
      <button
        class={task.working ? "status working-badge" : "status"}
        hx-post={workingPath}
        hx-vals={JSON.stringify({ working: task.working ? "false" : "true", version: task.version })}
        hx-target="#task-meta"
        hx-swap="innerHTML"
        aria-pressed={task.working ? "true" : "false"}
      >
        {task.working ? "working" : "not working"}
      </button>
      {children}
    </aside>
  );
};

const MetaRow: FC<{ label: string; path: string; spaced?: boolean }> = ({
  label,
  path,
  spaced,
}) => (
  <a
    class={`meta-row meta-row-link${spaced ? " meta-row--spaced" : ""}`}
    href={path}
    hx-get={path}
    hx-target="#task-meta"
    hx-swap="innerHTML"
  >
    <h2>{label}</h2>
    <span class="meta-caret" aria-hidden="true">
      ▾
    </span>
  </a>
);
