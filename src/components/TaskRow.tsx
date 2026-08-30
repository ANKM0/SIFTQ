import type { FC } from "hono/jsx";
import type { Task } from "../task";

export const TaskRow: FC<{ task: Task; issueNumber: number }> = ({ task, issueNumber }) => (
  <a class="task-row" href={`/tasks/${task.id}?from=tasks`}>
    <span class="issue-number">#{issueNumber}</span>
    <span class="task-row-main">
      <span class="task-row-title">
        <strong>{task.title}</strong>
        <span class="status area-badge">{task.area}</span>
        <span class={`status status--${task.status}`}>{task.status}</span>
      </span>
      <span class="muted">Matrix quadrant</span>
    </span>
  </a>
);
