import { TASK_AREAS } from "../task";
import type { Task } from "../task";
import { sortForMatrix } from "../task-list";
import { TaskCard } from "../components/TaskCard";
import { NewTaskLink } from "./navigation";

export function MatrixPage({ tasks }: { tasks: readonly Task[] }) {
  const matrixTasks = sortForMatrix(tasks);
  return (
    <div class="page page--matrix" data-state="normal">
      <div class="page-header">
        <div>
          <h1 class="page-title">Matrix</h1>
          <p class="muted">Organize tasks by urgency and importance.</p>
        </div>
        <NewTaskLink from="matrix" />
      </div>
      <p id="dnd-conflict" class="error" hidden>
        Task was updated elsewhere. The Matrix was restored to the latest state.
      </p>
      <div class="matrix matrix-axis" aria-label="Four status matrix">
        <div class="axis-line axis-line--horizontal" aria-hidden="true">
          <span>緊急度</span>
        </div>
        <div class="axis-line axis-line--vertical" aria-hidden="true">
          <span>重要度</span>
        </div>
        {TASK_AREAS.map((area) => (
          <a
            key={`overlay-${area}`}
            class={`matrix-create-link matrix-create-link--q${area}`}
            href={`/tasks/new?area=${area}&from=matrix`}
            aria-hidden="true"
            tabindex={-1}
          >
            <span aria-hidden="true"></span>
          </a>
        ))}
        {TASK_AREAS.map((area) => (
          <section
            key={area}
            class={`area area--quadrant area--q${area}`}
            aria-labelledby={`area-${area}`}
            data-drop-area={area}
          >
            <a class="area-create-link" href={`/tasks/new?area=${area}&from=matrix`} aria-label={`Create task in area ${area}`}>
              <span aria-hidden="true"></span>
            </a>
            <h2 id={`area-${area}`}>{area}</h2>
            <div class="matrix-cards" data-area={area} data-dnd-group="matrix">
              {matrixTasks
                .filter((task) => task.area === area)
                .map((task) => (
                  <TaskCard key={task.id} task={task} />
                ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
