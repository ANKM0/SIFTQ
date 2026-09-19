import type { JSX } from "hono/jsx/jsx-runtime";
import type { NewTaskFrom } from "../components/NewTaskMeta";

export function pageNav(path: string) {
  return {
    href: path,
    "hx-get": path,
    "hx-target": "#page",
    "hx-swap": "innerHTML",
    "hx-push-url": "true",
  };
}

export function NewTaskLink({ from }: { from: NewTaskFrom }): JSX.Element {
  return (
    <a class="button primary" {...pageNav(`/tasks/new?from=${from}`)}>
      New task
    </a>
  );
}
