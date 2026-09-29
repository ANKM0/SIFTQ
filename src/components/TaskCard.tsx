import type { FC } from "hono/jsx";
import { splitDescription } from "../description";
import { is_working } from "../task";
import type { Task } from "../task";

export const TaskCard: FC<{ task: Task }> = ({ task }) => {
  const segments = splitDescription(task.description);
  const text = segments
    .filter((segment) => !segment.src)
    .map((segment) => segment.text)
    .join("")
    .trim();
  const images = segments.flatMap((segment) => (segment.src ? [segment.src] : []));
  const remaining = images.length - 1;

  return (
    <a
      class={is_working(task) ? "task-card task-card--working" : "task-card"}
      data-task-id={task.id}
      data-version={task.version}
      draggable="false"
      href={`/tasks/${task.id}?from=matrix`}
    >
      <span class="task-card-header">
        <span class="task-title">{task.title}</span>
        {is_working(task) ? <span class="working-badge">working</span> : null}
      </span>
      {text === "" ? null : <span class="task-card-description">{text}</span>}
      {images.length === 0 ? null : (
        <span class="task-card-images">
          <img class="task-card-image description-image" src={images[0]} alt="" />
          {remaining > 0 ? <span class="task-card-image-count">{`+${remaining}`}</span> : null}
        </span>
      )}
    </a>
  );
};
