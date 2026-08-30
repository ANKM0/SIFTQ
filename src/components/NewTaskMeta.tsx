import type { FC } from "hono/jsx";
import { isTaskArea, isTaskStatus, TASK_AREAS, TASK_STATUSES } from "../task";
import type { TaskArea, TaskStatus } from "../task";
import { AREA_DOT_CLASSES, STATUS_DESCRIPTIONS, STATUS_DOT_CLASSES } from "./OptionMenu";

type OpenMenu = "status" | "area";

export type NewTaskState = {
  status: TaskStatus;
  area: TaskArea;
  openMenu: OpenMenu | undefined;
};

function newTaskPath(state: NewTaskState): string {
  const query = new URLSearchParams({ status: state.status, area: String(state.area) });
  if (state.openMenu !== undefined) query.set("menu", state.openMenu);
  return `/tasks/new?${query.toString()}`;
}

type NewTaskChoiceState = {
  selected: boolean;
  next: NewTaskState;
  dotClass: string;
  description: string;
};

function newTaskChoiceState(
  state: NewTaskState,
  menu: OpenMenu,
  value: string | number,
): NewTaskChoiceState | null {
  if (menu === "status" && isTaskStatus(value)) {
    return {
      selected: state.status === value,
      next: { ...state, status: value },
      dotClass: STATUS_DOT_CLASSES[value],
      description: STATUS_DESCRIPTIONS[value],
    };
  }
  if (menu === "area" && isTaskArea(value)) {
    return {
      selected: state.area === value,
      next: { ...state, area: value },
      dotClass: AREA_DOT_CLASSES[value],
      description: "Matrix quadrant.",
    };
  }
  return null;
}

const NewTaskChoice: FC<{
  state: NewTaskState;
  menu: OpenMenu;
  value: string | number;
}> = ({ state, menu, value }) => {
  const choice = newTaskChoiceState(state, menu, value);
  if (choice === null) return null;

  return (
    <a class={`status-choice${choice.selected ? " selected" : ""}`} href={newTaskPath(choice.next)}>
      {choice.selected ? <span class="check">✓</span> : <span class="box"></span>}
      <span class={choice.dotClass}></span>
      <span>
        <strong>{value}</strong>
        <br />
        <span class="muted">{choice.description}</span>
      </span>
    </a>
  );
};

export const NewTaskMeta: FC<{ state: NewTaskState }> = ({ state }) => {
  const openMenu = state.openMenu;
  const title = openMenu === "status" ? "Apply status to this task" : "Apply area to this task";
  const selectedTitle = openMenu === "status" ? "Selected status" : "Selected area";

  return (
    <aside
      id="new-task-meta"
      class={`side-panel${openMenu === undefined ? "" : " side-panel--popover-open"}`}
      data-popover-close-href={openMenu === undefined ? undefined : newTaskPath({ ...state, openMenu: undefined })}
    >
      <a class="meta-row meta-row-link" href={newTaskPath({ ...state, openMenu: "status" })}>
        <h2>Status</h2>
        <span class="meta-caret" aria-hidden="true">▾</span>
      </a>
      <a class={`status status--${state.status}`} href={newTaskPath({ ...state, openMenu: "status" })}>
        {state.status}
      </a>
      <a class="meta-row meta-row-link meta-row--spaced" href={newTaskPath({ ...state, openMenu: "area" })}>
        <h2>Area</h2>
        <span class="meta-caret" aria-hidden="true">▾</span>
      </a>
      <a class="status area-badge" href={newTaskPath({ ...state, openMenu: "area" })}>{state.area}</a>
      {openMenu === undefined ? null : (
        <section class="popover" aria-label={title}>
          <h3>{title}</h3>
          <div class="status-group-title">{selectedTitle}</div>
          {openMenu === "status" ? TASK_STATUSES.filter((value) => value === state.status).map((value) => (
            <NewTaskChoice key={value} state={state} menu="status" value={value} />
          )) : TASK_AREAS.filter((value) => value === state.area).map((value) => (
            <NewTaskChoice key={String(value)} state={state} menu="area" value={value} />
          ))}
          <div class="status-group-title">Suggestions</div>
          {openMenu === "status" ? TASK_STATUSES.filter((value) => value !== state.status).map((value) => (
            <NewTaskChoice key={value} state={state} menu="status" value={value} />
          )) : TASK_AREAS.filter((value) => value !== state.area).map((value) => (
            <NewTaskChoice key={String(value)} state={state} menu="area" value={value} />
          ))}
          <a class="status-choice" href={newTaskPath({ ...state, openMenu: undefined })}>Cancel</a>
        </section>
      )}
    </aside>
  );
};
