import type { FC } from "hono/jsx";
import { is_working } from "../task";
import type { Task } from "../task";

export const TaskRow: FC<{ task: Task; issueNumber: number }> = ({ task, issueNumber }) => (
  <div
    class={is_working(task) ? "task-row task-row--working" : "task-row"}
    data-task-row={task.id}
  >
    <label class="task-row-selection">
      <input
        type="checkbox"
        value={task.id}
        aria-label={`Select ${task.title}`}
        data-task-select
      />
    </label>
    <a class="task-row-link" href={`/tasks/${task.id}?from=tasks`}>
      <span class="issue-number">#{issueNumber}</span>
      <span class="task-row-main">
        <span class="task-row-title">
          <strong>{task.title}</strong>
          <span class="status area-badge">{task.area}</span>
          <span class={`status status--${task.status}`}>{task.status}</span>
          {is_working(task) ? <span class="working-badge">working</span> : null}
        </span>
        <span class="muted">Matrix quadrant</span>
      </span>
    </a>
  </div>
);
