import type { FC } from "hono/jsx";
import { TASK_AREAS, TASK_STATUSES } from "../task";
import type { Task, TaskArea, TaskStatus } from "../task";
import { TaskSidePanel } from "./TaskMeta";
import { AREA_DOT_CLASSES, STATUS_DESCRIPTIONS, STATUS_DOT_CLASSES } from "./task-option-data";

type Choice = {
  value: string | number;
  selected: boolean;
  description: string;
  dotClass: string;
};

function statusChoice(task: Task, value: TaskStatus): Choice {
  return {
    value,
    selected: value === task.status,
    description: STATUS_DESCRIPTIONS[value],
    dotClass: STATUS_DOT_CLASSES[value],
  };
}

function areaChoice(task: Task, value: TaskArea): Choice {
  return {
    value,
    selected: value === task.area,
    description: "Matrix quadrant.",
    dotClass: AREA_DOT_CLASSES[value],
  };
}

function buildChoices(task: Task, open: "status" | "area"): Choice[] {
  return open === "status"
    ? TASK_STATUSES.map((value) => statusChoice(task, value))
    : TASK_AREAS.map((value) => areaChoice(task, value));
}

function returnStatusSuffix(returnTo: "matrix" | "tasks", listStatus: TaskStatus): string {
  return returnTo === "matrix" ? "" : `&status=${listStatus}`;
}

const ChoiceLink: FC<{
  task: Task;
  open: "status" | "area";
  choice: Choice;
  returnTo: "matrix" | "tasks";
  listStatus: TaskStatus;
}> = ({
  task,
  open,
  choice,
  returnTo,
  listStatus,
}) => {
  const statusSuffix = returnStatusSuffix(returnTo, listStatus);
  return (
    <a
      class={`status-choice${choice.selected ? " selected" : ""}`}
      href={`/tasks/${task.id}?from=${returnTo}${statusSuffix}`}
      hx-post={`/tasks/${task.id}/${open}?from=${returnTo}${statusSuffix}`}
      hx-vals={JSON.stringify({ [open]: choice.value, version: task.version })}
      hx-target="#task-meta"
      hx-swap="innerHTML"
    >
      {choice.selected ? <span class="check">✓</span> : <span class="box"></span>}
      <span class={choice.dotClass}></span>
      <span>
        <strong>{choice.value}</strong>
        <br />
        <span class="muted">{choice.description}</span>
      </span>
    </a>
  );
};

export const OptionMenu: FC<{
  task: Task;
  open: "status" | "area";
  returnTo?: "matrix" | "tasks";
  listStatus?: TaskStatus;
}> = ({ task, open, returnTo = "tasks", listStatus = "do" }) => {
  const choices = buildChoices(task, open);
  const title = open === "status" ? "Apply status to this task" : "Apply area to this task";
  const selectedTitle = open === "status" ? "Selected status" : "Selected area";
  const selected = choices.filter((choice) => choice.selected);
  const suggestions = choices.filter((choice) => !choice.selected);
  const cancelHref = `/tasks/${task.id}?from=${returnTo}${returnStatusSuffix(returnTo, listStatus)}`;
  const renderChoice = (choice: Choice) => (
    <ChoiceLink
      key={String(choice.value)}
      task={task}
      open={open}
      choice={choice}
      returnTo={returnTo}
      listStatus={listStatus}
    />
  );

  return (
    <TaskSidePanel
      task={task}
      className="side-panel side-panel--popover-open"
      returnTo={returnTo}
      listStatus={listStatus}
    >
      <section class="popover" aria-label={title}>
        <h3>{title}</h3>
        <div class="status-group-title">{selectedTitle}</div>
        {selected.map(renderChoice)}
        <div class="status-group-title">Suggestions</div>
        {suggestions.map(renderChoice)}
        <a class="status-choice" href={cancelHref}>
          Cancel
        </a>
      </section>
    </TaskSidePanel>
  );
};
