import type { FC } from "hono/jsx";
import { is_working } from "../task";
import type { Task } from "../task";

export const TaskCard: FC<{ task: Task }> = ({ task }) => (
  <a
    class={is_working(task) ? "task-card task-card--working" : "task-card"}
    data-task-id={task.id}
    data-version={task.version}
    draggable="true"
    href={`/tasks/${task.id}?from=matrix`}
  >
    <span class="task-card-header">
      <span class="task-title">{task.title}</span>
      {is_working(task) ? <span class="working-badge">working</span> : null}
    </span>
  </a>
);
