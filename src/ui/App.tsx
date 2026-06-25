import { type FormEvent, useEffect, useState } from "react";
import {
  DndContext,
  type DragEndEvent,
  useDraggable,
  useDroppable
} from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";

import {
  type MatrixAreaId,
  type TerminalAreaId,
  type Task
} from "../contracts/task";
import { browserTaskRepository } from "../adapters/browserTaskRepository";
import {
  areaDropId,
  restrictDragToWindowEdges,
  resolveTaskDropOperation,
  taskDropId
} from "./dragDrop";
import {
  MATRIX_AREAS,
  TERMINAL_AREAS,
  tasksForArea,
  validateTaskTitleInput
} from "./taskPresentation";
import "./App.css";

const dragModifiers = [restrictDragToWindowEdges];
const DEFAULT_ROUTE = "#/";

type RuntimeState =
  | { readonly status: "checking" }
  | { readonly status: "ready" }
  | {
      readonly status: "storage-error";
      readonly code: string;
      readonly message: string;
    };

type AppRoute =
  | { readonly name: "matrix" }
  | { readonly name: "tasks" }
  | { readonly name: "task-detail"; readonly taskId: Task["id"] };

export function App() {
  const [tasks, setTasks] = useState<readonly Task[]>([]);
  const [runtimeState, setRuntimeState] = useState<RuntimeState>({
    status: "checking"
  });
  const [operationError, setOperationError] = useState<string | null>(null);
  const [route, setRoute] = useState<AppRoute>(() => routeFromHash(window.location.hash));

  useEffect(() => {
    let isCurrent = true;

    async function initialize() {
      try {
        const initialTasks = await browserTaskRepository.listTasks();

        if (!isCurrent) {
          return;
        }

        setTasks(initialTasks);
        setRuntimeState({ status: "ready" });
      } catch (error) {
        if (isCurrent) {
          setRuntimeState({
            code: codeForError(error),
            message: messageForError(error, "Browser task storage could not be opened."),
            status: "storage-error"
          });
        }
      }
    }

    void initialize();

    return () => {
      isCurrent = false;
    };
  }, []);

  useEffect(() => {
    function syncRouteFromHash() {
      setRoute(routeFromHash(window.location.hash));
    }

    window.addEventListener("hashchange", syncRouteFromHash);

    return () => {
      window.removeEventListener("hashchange", syncRouteFromHash);
    };
  }, []);

  async function handleCreateTask(
    areaId: MatrixAreaId,
    title: string
  ): Promise<string | null> {
    try {
      setOperationError(null);
      await browserTaskRepository.createTask({ areaId, title });
      await refreshTasks();

      return null;
    } catch (error) {
      return messageForError(error, "Task could not be created.");
    }
  }

  async function handleUpdateTaskTitle(
    taskId: Task["id"],
    title: string
  ): Promise<string | null> {
    try {
      setOperationError(null);
      await browserTaskRepository.updateTaskTitle({ taskId, title });
      await refreshTasks();

      return null;
    } catch (error) {
      return messageForError(error, "Task could not be updated.");
    }
  }

  async function handleDragEnd(event: DragEndEvent) {
    const operation = resolveTaskDropOperation(
      tasks,
      String(event.active.id),
      event.over === null ? null : String(event.over.id)
    );

    if (operation === null) {
      return;
    }

    try {
      if (operation.type === "move") {
        await browserTaskRepository.moveTask(operation);
      } else {
        await browserTaskRepository.reorderTask(operation);
      }

      setOperationError(null);
      await refreshTasks();
    } catch (error) {
      setOperationError(messageForError(error, "Task could not be moved."));
    }
  }

  async function refreshTasks() {
    setTasks(await browserTaskRepository.listTasks());
  }

  if (runtimeState.status === "checking") {
    return <RuntimeMessage title="Opening storage" message="Checking task storage." />;
  }

  if (runtimeState.status === "storage-error") {
    return (
      <RuntimeMessage
        title="Storage error"
        message={runtimeState.message}
        code={runtimeState.code}
      />
    );
  }

  return (
    <>
      {route.name === "matrix" ? (
        <DndContext
          autoScroll={false}
          modifiers={dragModifiers}
          onDragEnd={(event) => void handleDragEnd(event)}
        >
          <MatrixPage
            tasks={tasks}
            operationError={operationError}
            onCreateTask={handleCreateTask}
            onUpdateTaskTitle={handleUpdateTaskTitle}
          />
        </DndContext>
      ) : route.name === "tasks" ? (
        <TasksPage tasks={tasks} />
      ) : (
        <TaskDetailPage
          task={tasks.find((candidate) => candidate.id === route.taskId) ?? null}
        />
      )}
    </>
  );
}

type MatrixPageProps = {
  readonly tasks: readonly Task[];
  readonly operationError: string | null;
  readonly onCreateTask: (areaId: MatrixAreaId, title: string) => Promise<string | null>;
  readonly onUpdateTaskTitle: (
    taskId: Task["id"],
    title: string
  ) => Promise<string | null>;
};

function MatrixPage({
  tasks,
  operationError,
  onCreateTask,
  onUpdateTaskTitle
}: MatrixPageProps) {
  const [editingTask, setEditingTask] = useState<Task | null>(null);

  async function handleSaveTitle(title: string): Promise<string | null> {
    if (editingTask === null) {
      return "Task could not be updated.";
    }

    const updateError = await onUpdateTaskTitle(editingTask.id, title);

    if (updateError === null) {
      setEditingTask(null);
    }

    return updateError;
  }

  return (
    <main className="matrix-page">
      <AppHeader currentPage="matrix" />
      {operationError !== null ? (
        <p className="matrix-page__error" role="alert">
          {operationError}
        </p>
      ) : null}
      <section aria-label="Matrix workspace" className="matrix-workspace">
        <div className="matrix-workspace__status matrix-workspace__status--skipped">
          {TERMINAL_AREAS.filter((area) => area.id === "skipped").map((area) => (
            <StatusDropArea key={area.id} areaId={area.id} label={area.label} />
          ))}
        </div>
        <section aria-label="Task matrix" className="matrix-grid">
          {MATRIX_AREAS.map((area) => (
            <AreaPanel
              key={area.id}
              areaId={area.id}
              label={area.label}
              tasks={tasksForArea(tasks, area.id)}
              onCreateTask={(title) => onCreateTask(area.id, title)}
              onEditTask={setEditingTask}
            />
          ))}
        </section>
        <div className="matrix-workspace__status matrix-workspace__status--done">
          {TERMINAL_AREAS.filter((area) => area.id === "done").map((area) => (
            <StatusDropArea key={area.id} areaId={area.id} label={area.label} />
          ))}
        </div>
      </section>
      {editingTask !== null ? (
        <TaskTitleEditModal
          task={editingTask}
          onCancel={() => setEditingTask(null)}
          onSave={handleSaveTitle}
        />
      ) : null}
    </main>
  );
}

type TasksPageProps = {
  readonly tasks: readonly Task[];
};

function TasksPage({ tasks }: TasksPageProps) {
  return (
    <main className="matrix-page">
      <AppHeader currentPage="tasks" />
      <section aria-labelledby="tasks-page-title" className="tasks-page">
        <header className="tasks-page__header">
          <h2 id="tasks-page-title">タスク一覧</h2>
          <p>{tasks.length} tasks</p>
        </header>
        <ul aria-label="Task list" className="tasks-page__list">
          {tasks.map((task) => (
            <li key={task.id} className="tasks-page__item">
              <a className="tasks-page__link" href={`#/tasks/${task.id}`}>
                <span className="tasks-page__title">{task.title}</span>
                <span className="tasks-page__meta">
                  {task.areaId} / {task.status}
                </span>
              </a>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}

type TaskDetailPageProps = {
  readonly task: Task | null;
};

function TaskDetailPage({ task }: TaskDetailPageProps) {
  return (
    <main className="matrix-page">
      <AppHeader currentPage="tasks" />
      <section aria-labelledby="task-detail-title" className="task-detail-page">
        {task === null ? (
          <>
            <h2 id="task-detail-title">Task not found</h2>
            <p>指定された taskId は存在しないか、すでに削除されています。</p>
            <a className="tasks-page__back-link" href="#/tasks">
              タスク一覧へ戻る
            </a>
          </>
        ) : (
          <>
            <header className="task-detail-page__header">
              <h2 id="task-detail-title">{task.title}</h2>
              <a className="tasks-page__back-link" href="#/tasks">
                タスク一覧へ戻る
              </a>
            </header>
            <dl className="task-detail-page__meta">
              <div>
                <dt>Area</dt>
                <dd>{task.areaId}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>{task.status}</dd>
              </div>
              <div>
                <dt>Description</dt>
                <dd>{task.description.length > 0 ? task.description : "説明なし"}</dd>
              </div>
            </dl>
          </>
        )}
      </section>
    </main>
  );
}

type AppHeaderProps = {
  readonly currentPage: "matrix" | "tasks";
};

function AppHeader({ currentPage }: AppHeaderProps) {
  return (
    <header className="matrix-page__header">
      <div className="matrix-page__header-main">
        <h1>SIFTQ</h1>
        <nav aria-label="Primary">
          <a
            aria-current={currentPage === "matrix" ? "page" : undefined}
            className="matrix-page__nav-link"
            href={DEFAULT_ROUTE}
          >
            マトリックス
          </a>
          <a
            aria-current={currentPage === "tasks" ? "page" : undefined}
            className="matrix-page__nav-link"
            href="#/tasks"
          >
            タスク一覧
          </a>
        </nav>
      </div>
    </header>
  );
}

type AreaPanelProps = {
  readonly areaId: MatrixAreaId;
  readonly label: string;
  readonly tasks: readonly Task[];
  readonly onCreateTask: (title: string) => Promise<string | null>;
  readonly onEditTask: (task: Task) => void;
};

function AreaPanel({ areaId, label, tasks, onCreateTask, onEditTask }: AreaPanelProps) {
  const { isOver, setNodeRef } = useDroppable({ id: areaDropId(areaId) });
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const validationError = validateTaskTitleInput(title);
  const canCreateTask = validationError === null;
  const panelClassName = [
    "area-panel",
    `area-panel--${areaId}`,
    isOver ? "area-panel--drop-target" : "",
    tasks.length === 0 ? "area-panel--empty" : ""
  ]
    .filter(Boolean)
    .join(" ");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (validationError !== null) {
      setError(validationError);
      return;
    }

    const createError = await onCreateTask(title);

    if (createError === null) {
      setTitle("");
    }

    setError(createError);
  }

  return (
    <article className={panelClassName}>
      <header className="area-panel__header">
        <div>
          <h2>{label}</h2>
          <p aria-label={`${label} task count`}>{tasks.length} cards</p>
        </div>
      </header>
      <form
        aria-label={`Create task in ${label}`}
        className="task-create-form"
        onSubmit={(event) => void handleSubmit(event)}
      >
        <input
          aria-label={`New task title for ${label}`}
          className="task-create-form__input"
          type="text"
          value={title}
          onChange={(event) => {
            setTitle(event.target.value);
            setError(null);
          }}
        />
        <button
          aria-label={`Add task to ${label}`}
          className="area-panel__add"
          disabled={!canCreateTask}
          type="submit"
        >
          +
        </button>
      </form>
      {validationError !== null && Array.from(title).length > 0 ? (
        <p className="task-create-form__error" role="alert">
          {validationError}
        </p>
      ) : null}
      {error !== null ? (
        <p className="task-create-form__error" role="alert">
          {error}
        </p>
      ) : null}
      <ul ref={setNodeRef} aria-label={`${label} tasks`} className="area-panel__tasks">
        {tasks.length === 0 ? (
          <li aria-hidden="true" className="area-panel__empty">
            No cards
          </li>
        ) : (
          tasks.map((task) => (
            <TaskCard key={task.id} task={task} onEditTask={onEditTask} />
          ))
        )}
      </ul>
    </article>
  );
}

type TaskCardProps = {
  readonly task: Task;
  readonly onEditTask: (task: Task) => void;
};

function TaskCard({ task, onEditTask }: TaskCardProps) {
  const draggable = useDraggable({ id: taskDropId(task.id) });
  const droppable = useDroppable({ id: taskDropId(task.id) });
  const className = [
    "task-card",
    draggable.isDragging ? "task-card--dragging" : "",
    droppable.isOver ? "task-card--drop-target" : ""
  ]
    .filter(Boolean)
    .join(" ");
  const style = {
    cursor: "grab",
    transform: CSS.Translate.toString(draggable.transform)
  };

  return (
    <li
      className={className}
      ref={(node) => {
        draggable.setNodeRef(node);
        droppable.setNodeRef(node);
      }}
      style={style}
      {...draggable.listeners}
      {...draggable.attributes}
    >
      <span className="task-card__title">{task.title}</span>
      <button
        className="task-card__edit"
        type="button"
        onClick={() => onEditTask(task)}
        onPointerDown={(event) => event.stopPropagation()}
      >
        Edit
      </button>
    </li>
  );
}

type TaskTitleEditModalProps = {
  readonly task: Task;
  readonly onCancel: () => void;
  readonly onSave: (title: string) => Promise<string | null>;
};

function TaskTitleEditModal({ task, onCancel, onSave }: TaskTitleEditModalProps) {
  const [title, setTitle] = useState(task.title);
  const [error, setError] = useState<string | null>(null);
  const validationError = validateTaskTitleInput(title);
  const canSave = validationError === null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!canSave) {
      setError(validationError);
      return;
    }

    setError(await onSave(title));
  }

  return (
    <div className="task-edit-modal" role="presentation">
      <section
        aria-labelledby="task-edit-modal-title"
        aria-modal="true"
        className="task-edit-modal__dialog"
        role="dialog"
      >
        <h2 id="task-edit-modal-title">Edit task title</h2>
        <form className="task-edit-form" onSubmit={(event) => void handleSubmit(event)}>
          <label className="task-edit-form__label">
            Title
            <input
              aria-label="Task title"
              className="task-edit-form__input"
              type="text"
              value={title}
              onChange={(event) => {
                setTitle(event.target.value);
                setError(null);
              }}
            />
          </label>
          {validationError !== null ? (
            <p className="task-edit-form__error" role="alert">
              {validationError}
            </p>
          ) : null}
          {error !== null ? (
            <p className="task-edit-form__error" role="alert">
              {error}
            </p>
          ) : null}
          <div className="task-edit-form__actions">
            <button type="button" onClick={onCancel}>
              Cancel
            </button>
            <button disabled={!canSave} type="submit">
              Save
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

type StatusDropAreaProps = {
  readonly areaId: TerminalAreaId;
  readonly label: string;
};

function StatusDropArea({ areaId, label }: StatusDropAreaProps) {
  const { isOver, setNodeRef } = useDroppable({ id: areaDropId(areaId) });
  const className = [
    "status-drop-area",
    isOver ? "status-drop-area--drop-target" : ""
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <article ref={setNodeRef} className={className}>
      <h2>{label}</h2>
      <p>0 cards</p>
    </article>
  );
}

type RuntimeMessageProps = {
  readonly title: string;
  readonly message: string;
  readonly code?: string;
};

function RuntimeMessage({ title, message, code }: RuntimeMessageProps) {
  return (
    <main className="matrix-page matrix-page--runtime-message">
      <section className="runtime-message" role="status">
        <h1>{title}</h1>
        {code === undefined ? null : <p className="runtime-message__code">{code}</p>}
        <p>{message}</p>
      </section>
    </main>
  );
}

function messageForError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function codeForError(error: unknown): string {
  return typeof error === "object" &&
    error !== null &&
    "code" in error &&
    typeof error.code === "string"
    ? error.code
    : "STORAGE";
}

function routeFromHash(hash: string): AppRoute {
  const normalizedHash = hash.length > 0 ? hash : DEFAULT_ROUTE;

  if (normalizedHash === DEFAULT_ROUTE || normalizedHash === "#") {
    return { name: "matrix" };
  }

  if (normalizedHash === "#/tasks") {
    return { name: "tasks" };
  }

  const taskMatch = normalizedHash.match(/^#\/tasks\/(.+)$/u);

  if (taskMatch !== null) {
    return { name: "task-detail", taskId: decodeURIComponent(taskMatch[1]) };
  }

  return { name: "matrix" };
}
