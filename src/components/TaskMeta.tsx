import type { FC } from "hono/jsx";
import type { Task } from "../task";

export const TaskMeta: FC<{ task: Task }> = ({ task }) => (
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
