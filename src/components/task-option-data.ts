import type { TaskArea, TaskStatus } from "../task";

export const STATUS_DESCRIPTIONS: Record<TaskStatus, string> = {
  do: "Visible on the matrix.",
  done: "Completed. Area is preserved.",
  skip: "Skipped. Area is preserved.",
};

export const STATUS_DOT_CLASSES: Record<TaskStatus, string> = {
  do: "status-dot status-dot--do",
  done: "status-dot status-dot--done",
  skip: "status-dot status-dot--skip",
};

export const AREA_DOT_CLASSES: Record<TaskArea, string> = {
  1: "status-dot status-dot--one",
  2: "status-dot status-dot--two",
  3: "status-dot status-dot--three",
  4: "status-dot status-dot--four",
};
