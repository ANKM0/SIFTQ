import type { FC } from "hono/jsx";
import type { Task } from "../task";

export const TaskCard: FC<{ task: Task }> = ({ task }) => (
  <a
    class="task-card"
    data-task-id={task.id}
    data-version={task.version}
    href={`/tasks/${task.id}`}
  >
    <span class="task-title">{task.title}</span>
  </a>
);
