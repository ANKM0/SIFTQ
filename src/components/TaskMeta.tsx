import type { FC } from "hono/jsx";
import type { JSX } from "hono/jsx/jsx-runtime";
import type { Task } from "../task";

export const TaskMeta: FC<{ task: Task; returnTo?: "matrix" | "tasks" }> = ({
  task,
  returnTo,
}) => {
  if (returnTo === undefined) return <TaskSidePanel task={task} />;
  return <TaskSidePanel task={task} returnTo={returnTo} />;
};

export const TaskSidePanel: FC<{
  task: Task;
  className?: string;
  children?: JSX.Element;
  returnTo?: "matrix" | "tasks";
}> = ({
  task,
  className = "side-panel",
  children,
  returnTo = "tasks",
}) => {
  const detailPath = `/tasks/${task.id}?from=${returnTo}`;
  const statusPath = `/tasks/${task.id}/status/menu?from=${returnTo}`;
  const areaPath = `/tasks/${task.id}/area/menu?from=${returnTo}`;

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
