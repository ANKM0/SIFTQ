import type { FC } from "hono/jsx";
import { TASK_AREAS, TASK_STATUSES } from "../task";
import type { TaskArea, TaskStatus } from "../task";
import { AREA_DOT_CLASSES, STATUS_DESCRIPTIONS, STATUS_DOT_CLASSES } from "./OptionMenu";

export type NewTaskFrom = "matrix" | "tasks";

export type NewTaskState = {
  status: TaskStatus;
  area: TaskArea;
  from: NewTaskFrom;
};

const NewTaskStatusChoice: FC<{ status: TaskStatus; selected: TaskStatus }> = ({ status, selected }) => (
  <label class={`status-choice${status === selected ? " selected" : ""}`}>
    <input type="radio" name="status" value={status} checked={status === selected} />
    <span class={STATUS_DOT_CLASSES[status]}></span>
    <span>
      <strong>{status}</strong>
      <br />
      <span class="muted">{STATUS_DESCRIPTIONS[status]}</span>
    </span>
  </label>
);

const NewTaskAreaChoice: FC<{ area: TaskArea; selected: TaskArea }> = ({ area, selected }) => (
  <label class={`status-choice${area === selected ? " selected" : ""}`}>
    <input type="radio" name="area" value={area} checked={area === selected} />
    <span class={AREA_DOT_CLASSES[area]}></span>
    <span>
      <strong>{area}</strong>
      <br />
      <span class="muted">Matrix quadrant.</span>
    </span>
  </label>
);

export const NewTaskMeta: FC<{ state: NewTaskState }> = ({ state }) => {
  return (
    <aside id="new-task-meta" class="side-panel side-panel--popover-open">
      <details>
        <summary class="meta-row meta-row-link">
          <h2>Status</h2>
          <span class={`status status--${state.status}`}>{state.status}</span>
        </summary>
        <section class="popover" aria-label="Apply status to this task">
          <h3>Apply status to this task</h3>
          {TASK_STATUSES.map((status) => <NewTaskStatusChoice key={status} status={status} selected={state.status} />)}
        </section>
      </details>
      <details>
        <summary class="meta-row meta-row-link meta-row--spaced">
          <h2>Area</h2>
          <span class="status area-badge">{state.area}</span>
        </summary>
        <section class="popover" aria-label="Apply area to this task">
          <h3>Apply area to this task</h3>
          {TASK_AREAS.map((area) => <NewTaskAreaChoice key={area} area={area} selected={state.area} />)}
        </section>
      </details>
    </aside>
  );
};
