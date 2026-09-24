import { splitDescription } from "../description";
import { TaskMeta } from "../components/TaskMeta";
import { NewTaskMeta } from "../components/NewTaskMeta";
import type { NewTaskState } from "../components/NewTaskMeta";
import type { Task } from "../task";

function TitleField({ value }: { value?: string }) {
  return (
    <label>
      Title
      <input type="text" name="title" value={value} maxlength={256} required />
    </label>
  );
}

function DescriptionField({ children }: { children?: string }) {
  const description = children ?? "";
  return (
    <>
      <label>
        Description
        <div
          aria-label="Description"
          class="description-editor"
          contenteditable={true}
          data-description-editor
          role="textbox"
          aria-multiline="true"
        >
          {splitDescription(description).map((segment, index) =>
            segment.href ? (
              <a key={index} href={segment.href}>
                {segment.text}
              </a>
            ) : (
              segment.text
            ),
          )}
        </div>
      </label>
      <textarea name="description" data-description-value hidden>
        {description}
      </textarea>
    </>
  );
}

export function TaskVersionInput({ version, outOfBand = false }: { version: number; outOfBand?: boolean }) {
  return (
    <input
      id="task-version"
      type="hidden"
      name="version"
      value={version}
      hx-swap-oob={outOfBand ? "true" : undefined}
    />
  );
}

function TaskFormActions({ submitLabel, cancelHref }: { submitLabel: string; cancelHref: string }) {
  return (
    <div class="form-actions">
      <a class="button" href={cancelHref}>
        Cancel
      </a>
      <button class="button primary" type="submit">
        {submitLabel}
      </button>
    </div>
  );
}

export function NewTaskForm({ state, error }: { state: NewTaskState; error?: string }) {
  return (
    <div class="page page--new" data-state="normal">
      <div class="page-header">
        <h1 class="page-title">New task</h1>
      </div>
      <form class="detail-grid" data-task-form="new" hx-post="/tasks" hx-target="#page" hx-swap="innerHTML">
        <div class="form-panel">
          <TitleField />
          <input type="hidden" name="from" value={state.from} />
          {error ? <p class="error">{error}</p> : null}
          <DescriptionField />
          <TaskFormActions submitLabel="Create" cancelHref={state.from === "matrix" ? "/matrix" : "/tasks"} />
        </div>
        <NewTaskMeta state={state} />
      </form>
    </div>
  );
}

export function TaskDetailPage({
  task,
  error,
  returnTo = "tasks",
}: {
  task: Task;
  error?: string;
  returnTo?: "matrix" | "tasks";
}) {
  const cancelHref = returnTo === "matrix" ? "/matrix" : "/tasks";

  return (
    <div class="page page--detail" data-state="normal">
      <div class="page-header">
        <h1 class="page-title">Task detail</h1>
        <a class="button" href={cancelHref}>
          Tasks
        </a>
      </div>
      <div class="detail-grid">
        <form
          class="form-panel"
          data-task-form="edit"
          method="post"
          action={`/tasks/${task.id}?from=${returnTo}`}
          hx-post={`/tasks/${task.id}?from=${returnTo}`}
          hx-target="#page"
          hx-swap="innerHTML"
        >
          <TitleField value={task.title} />
          <TaskVersionInput version={task.version} />
          {error ? <p class="error">{error}</p> : null}
          <DescriptionField>{task.description}</DescriptionField>
          <TaskFormActions submitLabel="Save" cancelHref={cancelHref} />
        </form>
        <TaskMeta task={task} returnTo={returnTo} />
      </div>
    </div>
  );
}
