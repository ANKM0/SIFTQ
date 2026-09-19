import { BASE_CSS } from "./styles/base";
import { COMMON_CSS, LOGIN_CSS } from "./styles/login";
import { MATRIX_ACTIONS_CSS, MATRIX_CSS } from "./styles/matrix";
import { TASK_FORM_CSS } from "./styles/task-form";
import { TASK_LIST_CSS, TASK_LIST_RESPONSIVE_CSS } from "./styles/task-list";

export const STYLES_CSS =
  BASE_CSS +
  "\n" +
  MATRIX_CSS.slice(1) +
  TASK_LIST_CSS.slice(1) +
  TASK_FORM_CSS.slice(1) +
  MATRIX_ACTIONS_CSS.slice(1) +
  COMMON_CSS +
  TASK_LIST_RESPONSIVE_CSS +
  LOGIN_CSS;
