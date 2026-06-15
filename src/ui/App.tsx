import { type FormEvent, useEffect, useRef, useState } from "react";
import {
  DndContext,
  type DragEndEvent,
  useDraggable,
  useDroppable
} from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";

import { InMemorySettingsRepository } from "../adapters/inMemorySettingsRepository";
import { InMemoryTaskRepository } from "../adapters/inMemoryTaskRepository";
import {
  loadAreaLabels,
  restoreDefaultAreaLabels,
  saveAreaLabels
} from "../application/settingsOperations";
import {
  createTask,
  listTasks,
  moveTask,
  reorderTask,
  updateTaskTitle
} from "../application/taskOperations";
import {
  INITIAL_AREAS,
  type Area,
  type MatrixAreaId,
  type TerminalAreaId
} from "../domain/area";
import {
  areasWithLabels,
  getDefaultAreaLabelSettings,
  type AreaLabelSettings
} from "../domain/settings";
import {
  isTaskVisibleInMatrix,
  TASK_TITLE_MAX_LENGTH,
  type Task
} from "../domain/task";
import { type SettingsRepository } from "../ports/settingsRepository";
import { type TaskRepository } from "../ports/taskRepository";
import {
  areaDropId,
  restrictDragToWindowEdges,
  resolveTaskDropOperation,
  taskDropId
} from "./dragDrop";
import "./App.css";

const dragModifiers = [restrictDragToWindowEdges];

type AppProps = {
  repository?: TaskRepository;
  settingsRepository?: SettingsRepository;
};

type Page = "matrix" | "settings";

export function App({ repository, settingsRepository }: AppProps) {
  const ownedRepository = useRef(new InMemoryTaskRepository());
  const ownedSettingsRepository = useRef(new InMemorySettingsRepository());
  const settingsRequestVersion = useRef(0);
  const activeRepository = repository ?? ownedRepository.current;
  const activeSettingsRepository =
    settingsRepository ?? ownedSettingsRepository.current;
  const [tasks, setTasks] = useState<readonly Task[]>([]);
  const [areaLabels, setAreaLabels] = useState<AreaLabelSettings>(
    getDefaultAreaLabelSettings()
  );
  const [page, setPage] = useState<Page>("matrix");

  useEffect(() => {
    void refreshTasks(activeRepository, setTasks);
  }, [activeRepository]);

  useEffect(() => {
    const requestVersion = settingsRequestVersion.current + 1;
    settingsRequestVersion.current = requestVersion;

    void refreshAreaLabels(
      activeSettingsRepository,
      setAreaLabels,
      requestVersion,
      settingsRequestVersion
    );
  }, [activeSettingsRepository]);

  async function handleCreateTask(
    areaId: MatrixAreaId,
    title: string
  ): Promise<string | null> {
    try {
      await createTask(activeRepository, { areaId, title });
      await refreshTasks(activeRepository, setTasks);

      return null;
    } catch (error) {
      return error instanceof Error ? error.message : "Task could not be created.";
    }
  }

  async function handleUpdateTaskTitle(
    taskId: Task["id"],
    title: string
  ): Promise<string | null> {
    try {
      await updateTaskTitle(activeRepository, { taskId, title });
      await refreshTasks(activeRepository, setTasks);

      return null;
    } catch (error) {
      return error instanceof Error ? error.message : "Task could not be updated.";
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

    if (operation.type === "move") {
      await moveTask(activeRepository, operation);
    } else {
      await reorderTask(activeRepository, operation);
    }

    await refreshTasks(activeRepository, setTasks);
  }

  async function handleSaveAreaLabels(
    labels: AreaLabelSettings
  ): Promise<string | null> {
    const requestVersion = settingsRequestVersion.current + 1;
    settingsRequestVersion.current = requestVersion;

    try {
      const savedLabels = await saveAreaLabels(activeSettingsRepository, labels);

      if (settingsRequestVersion.current === requestVersion) {
        setAreaLabels(savedLabels);
      }

      return null;
    } catch (error) {
      return error instanceof Error ? error.message : "Area labels could not be saved.";
    }
  }

  async function handleRestoreDefaultAreaLabels(): Promise<string | null> {
    const requestVersion = settingsRequestVersion.current + 1;
    settingsRequestVersion.current = requestVersion;

    try {
      const restoredLabels = await restoreDefaultAreaLabels(activeSettingsRepository);

      if (settingsRequestVersion.current === requestVersion) {
        setAreaLabels(restoredLabels);
      }

      return null;
    } catch (error) {
      return error instanceof Error
        ? error.message
        : "Area labels could not be restored.";
    }
  }

  const areas = areasWithLabels(areaLabels);

  return (
    <DndContext
      autoScroll={false}
      modifiers={dragModifiers}
      onDragEnd={(event) => void handleDragEnd(event)}
    >
      {page === "matrix" ? (
        <MatrixPage
          areas={areas}
          tasks={tasks}
          onCreateTask={handleCreateTask}
          onOpenSettings={() => setPage("settings")}
          onUpdateTaskTitle={handleUpdateTaskTitle}
        />
      ) : (
        <SettingsPage
          areaLabels={areaLabels}
          onBack={() => setPage("matrix")}
          onRestoreDefaults={handleRestoreDefaultAreaLabels}
          onSave={handleSaveAreaLabels}
        />
      )}
    </DndContext>
  );
}

type MatrixPageProps = {
  readonly areas: readonly Area[];
  readonly tasks: readonly Task[];
  readonly onCreateTask: (areaId: MatrixAreaId, title: string) => Promise<string | null>;
  readonly onOpenSettings: () => void;
  readonly onUpdateTaskTitle: (
    taskId: Task["id"],
    title: string
  ) => Promise<string | null>;
};

function MatrixPage({
  areas,
  tasks,
  onCreateTask,
  onOpenSettings,
  onUpdateTaskTitle
}: MatrixPageProps) {
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const matrixAreas = areas.filter(isMatrixAreaModel);
  const skippedArea = areas.find((area) => area.id === "skipped");
  const doneArea = areas.find((area) => area.id === "done");

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
      <header className="matrix-page__header">
        <h1>SIFTQ</h1>
        <button
          className="matrix-page__settings-button"
          type="button"
          onClick={onOpenSettings}
        >
          Settings
        </button>
      </header>
      <section aria-label="Matrix workspace" className="matrix-workspace">
        <div className="matrix-workspace__status matrix-workspace__status--skipped">
          {skippedArea === undefined ? null : (
            <StatusDropArea
              areaId="skipped"
              label={skippedArea.label}
            />
          )}
        </div>
        <section aria-label="Task matrix" className="matrix-grid">
          {matrixAreas.map((area) => (
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
          {doneArea === undefined ? null : (
            <StatusDropArea
              areaId="done"
              label={doneArea.label}
            />
          )}
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

type SettingsPageProps = {
  readonly areaLabels: AreaLabelSettings;
  readonly onBack: () => void;
  readonly onRestoreDefaults: () => Promise<string | null>;
  readonly onSave: (labels: AreaLabelSettings) => Promise<string | null>;
};

function SettingsPage({
  areaLabels,
  onBack,
  onRestoreDefaults,
  onSave
}: SettingsPageProps) {
  const [draftLabels, setDraftLabels] = useState<AreaLabelSettings>(areaLabels);
  const [error, setError] = useState<string | null>(null);
  const areas = areasWithLabels(areaLabels);
  const canSave = INITIAL_AREAS.every(
    (area) => draftLabels[area.id].trim().length > 0
  );

  useEffect(() => {
    setDraftLabels(areaLabels);
  }, [areaLabels]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!canSave) {
      setError("Area label must not be empty.");
      return;
    }

    setError(await onSave(draftLabels));
  }

  async function handleRestoreDefaults() {
    setError(await onRestoreDefaults());
  }

  return (
    <main className="matrix-page settings-page">
      <header className="matrix-page__header">
        <h1>Settings</h1>
        <button
          className="matrix-page__settings-button"
          type="button"
          onClick={onBack}
        >
          Matrix
        </button>
      </header>
      <section aria-labelledby="area-label-settings-title" className="settings-panel">
        <h2 id="area-label-settings-title">Area labels</h2>
        <form className="settings-form" onSubmit={(event) => void handleSubmit(event)}>
          <div className="settings-form__fields">
            {areas.map((area) => (
              <label key={area.id} className="settings-form__label">
                {area.role}
                <input
                  aria-label={`${area.label} label`}
                  className="settings-form__input"
                  type="text"
                  value={draftLabels[area.id]}
                  onChange={(event) => {
                    setDraftLabels((currentLabels) => ({
                      ...currentLabels,
                      [area.id]: event.target.value
                    }));
                    setError(null);
                  }}
                />
              </label>
            ))}
          </div>
          {!canSave ? (
            <p className="settings-form__error" role="alert">
              Area label must not be empty.
            </p>
          ) : null}
          {error !== null ? (
            <p className="settings-form__error" role="alert">
              {error}
            </p>
          ) : null}
          <div className="settings-form__actions">
            <button type="button" onClick={() => void handleRestoreDefaults()}>
              Restore defaults
            </button>
            <button disabled={!canSave} type="submit">
              Save labels
            </button>
          </div>
        </form>
      </section>
    </main>
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
  const trimmedTitle = title.trim();
  const isTitleTooLong = title.length > TASK_TITLE_MAX_LENGTH;
  const canCreateTask = trimmedTitle.length > 0 && !isTitleTooLong;
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

    if (trimmedTitle.length === 0) {
      setError("Task title must not be empty.");
      return;
    }

    if (isTitleTooLong) {
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
      {isTitleTooLong ? (
        <p className="task-create-form__error" role="alert">
          Title must be {TASK_TITLE_MAX_LENGTH} characters or less.
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
  const trimmedTitle = title.trim();
  const isBlank = trimmedTitle.length === 0;
  const isTitleTooLong = title.length > TASK_TITLE_MAX_LENGTH;
  const validationError = isBlank
    ? "Task title must not be empty."
    : isTitleTooLong
      ? `Title must be ${TASK_TITLE_MAX_LENGTH} characters or less.`
      : null;
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

async function refreshTasks(
  repository: TaskRepository,
  setTasks: (tasks: readonly Task[]) => void
) {
  setTasks(await listTasks(repository));
}

async function refreshAreaLabels(
  repository: SettingsRepository,
  setAreaLabels: (labels: AreaLabelSettings) => void,
  requestVersion: number,
  settingsRequestVersion: { current: number }
) {
  const labels = await loadAreaLabels(repository);

  if (settingsRequestVersion.current === requestVersion) {
    setAreaLabels(labels);
  }
}

function tasksForArea(tasks: readonly Task[], areaId: MatrixAreaId): Task[] {
  return tasks
    .filter((task) => task.areaId === areaId && isTaskVisibleInMatrix(task))
    .sort((left, right) => left.order - right.order);
}

function isMatrixAreaModel(area: Area): area is Area & { id: MatrixAreaId } {
  return area.kind === "matrix";
}
