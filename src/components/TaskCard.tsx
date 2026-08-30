import type { FC } from "hono/jsx";
import type { Task } from "../task";

export const TaskCard: FC<{ task: Task }> = ({ task }) => (
  <a
    class="task-card"
    data-task-id={task.id}
    data-version={task.version}
    draggable="true"
    href={`/tasks/${task.id}?from=matrix`}
  >
    <span class="task-card-header">
      <span class="task-title">{task.title}</span>
      <span class={`status status--${task.status}`}>{task.status}</span>
    </span>
  </a>
);
