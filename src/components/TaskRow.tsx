import type { FC } from "hono/jsx";
import type { Task } from "../task";

export const TaskRow: FC<{ task: Task }> = ({ task }) => (
  <li class="task-row">
    <a class="task-link" href={`/tasks/${task.id}`}>
      <span class="task-id">{task.id}</span>
      <span class="task-title">{task.title}</span>
      <span class="task-area">Area {task.area}</span>
      <span class="task-status">{task.status}</span>
    </a>
  </li>
);
