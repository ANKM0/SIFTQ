import type { D1Database } from "@cloudflare/workers-types";
import type { TaskRepository } from "./repository/task-repository";

export type Env = {
  TASK_REPOSITORY?: TaskRepository;
  DB?: D1Database;
  AUTH_PASSWORD?: string;
  SESSION_SECRET?: string;
  PREVIEW_MODE?: string;
};

export type AppEnv = {
  Bindings: Env;
};
