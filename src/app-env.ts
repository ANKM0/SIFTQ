import type { D1Database } from "@cloudflare/workers-types";
import type { TaskRepository } from "./repository/task-repository";
import type { IdeaRepository } from "./repository/idea-repository";
import type { ImageRepository } from "./repository/image-repository";

export type Env = {
  TASK_REPOSITORY?: TaskRepository;
  IDEA_REPOSITORY?: IdeaRepository;
  IMAGE_REPOSITORY?: ImageRepository;
  DB?: D1Database;
  AUTH_PASSWORD?: string;
  SESSION_SECRET?: string;
  PREVIEW_MODE?: string;
};

export type AppEnv = {
  Bindings: Env;
};
