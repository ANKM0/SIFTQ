import { Hono } from "hono";
import type { TaskRepository } from "./task-repository";

type Env = {
  Bindings: {
    TASK_REPOSITORY?: TaskRepository;
  };
};

const app = new Hono<Env>();

app.get("/", (c) => c.text("ok"));

export default app;
