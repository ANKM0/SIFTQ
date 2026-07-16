import { type FormEvent, useEffect, useRef, useState } from "react";
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
  matrixCollisionDetection,
  TASK_LIST_DROP_ID,
  restrictDragToWindowEdges,
  resolveTaskListDropIndex,
  resolveTaskDropOperation,
  taskDropId
} from "./dragDrop";
import {
  MATRIX_AREAS,
  findArea,
  tasksForArea,
  validateTaskTitleInput
} from "./taskPresentation";
import { normalizeTaskAreaId } from "../domain/taskRules";
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
  const [taskListNotice, setTaskListNotice] = useState<string | null>(null);
  const [runtimeState, setRuntimeState] = useState<RuntimeState>({
    status: "checking"
  });
  const [operationError, setOperationError] = useState<string | null>(null);
  const [route, setRoute] = useState<AppRoute>(() => routeFromHash(window.location.hash));
  const previousRouteRef = useRef<AppRoute>(route);

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

  useEffect(() => {
    if (
      previousRouteRef.current.name === "tasks" &&
      route.name !== "tasks" &&
      taskListNotice !== null
    ) {
      setTaskListNotice(null);
    }

    previousRouteRef.current = route;
  }, [route, taskListNotice]);

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
      } else if (operation.type === "update-status") {
        await browserTaskRepository.updateTaskStatus(operation);
      } else {
        await browserTaskRepository.reorderTask(operation);
      }

      setOperationError(null);
      await refreshTasks();
    } catch (error) {
      setOperationError(messageForError(error, "Task could not be moved."));
    }
  }

  async function handleTaskListDragEnd(event: DragEndEvent) {
    const toIndex = resolveTaskListDropIndex(
      tasks,
      String(event.active.id),
      event.over === null ? null : String(event.over.id)
    );

    if (toIndex === null) {
      return;
    }

    try {
      setOperationError(null);
      setTaskListNotice(null);
      await browserTaskRepository.reorderTaskList({
        taskId: String(event.active.id).replace(/^task:/, ""),
        toIndex
      });
      await refreshTasks();
    } catch (error) {
      setOperationError(messageForError(error, "Task list order could not be updated."));
    }
  }

  async function handleUpdateTaskStatus(taskId: Task["id"], status: Task["status"]) {
    try {
      setOperationError(null);
      setTaskListNotice(null);
      await browserTaskRepository.updateTaskStatus({ taskId, status });
      await refreshTasks();
    } catch (error) {
      setOperationError(messageForError(error, "Task status could not be updated."));
    }
  }

  async function handleUpdateTaskDetails(
    taskId: Task["id"],
    details: {
      title: Task["title"];
      description: Task["description"];
      areaId: MatrixAreaId;
      status: Task["status"];
    }
  ): Promise<string | null> {
    try {
      setOperationError(null);
      setTaskListNotice(null);
      await browserTaskRepository.updateTaskDetails({
        taskId,
        title: details.title,
        description: details.description,
        areaId: details.areaId,
        status: details.status
      });
      await refreshTasks();

      return null;
    } catch (error) {
      return messageForError(error, "Task details could not be updated.");
    }
  }

  async function handleDeleteTask(task: Task): Promise<boolean> {
    const shouldDelete = window.confirm(`"${task.title}" を削除しますか?`);

    if (!shouldDelete) {
      return false;
    }

    try {
      setOperationError(null);
      await browserTaskRepository.deleteTask({ taskId: task.id });
      setTaskListNotice("タスクを削除しました");
      await refreshTasks();
      window.location.hash = "#/tasks";

      return true;
    } catch (error) {
      setOperationError(messageForError(error, "Task could not be deleted."));

      return false;
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
          collisionDetection={matrixCollisionDetection}
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
        <DndContext
          autoScroll={false}
          modifiers={dragModifiers}
          onDragEnd={(event) => void handleTaskListDragEnd(event)}
        >
          <TasksPage
            tasks={tasks}
            notice={taskListNotice}
            operationError={operationError}
            onDeleteTask={handleDeleteTask}
            onUpdateTaskStatus={handleUpdateTaskStatus}
          />
        </DndContext>
      ) : (
        <TaskDetailPage
          operationError={operationError}
          onDeleteTask={handleDeleteTask}
          onUpdateTaskDetails={handleUpdateTaskDetails}
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
        <StatusDropArea areaId="skipped" label="Skipped" />
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
        <StatusDropArea areaId="done" label="Done" />
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
  readonly notice: string | null;
  readonly operationError: string | null;
  readonly onDeleteTask: (task: Task) => Promise<boolean>;
  readonly onUpdateTaskStatus: (taskId: Task["id"], status: Task["status"]) => Promise<void>;
};

function TasksPage({
  tasks,
  notice,
  operationError,
  onDeleteTask,
  onUpdateTaskStatus
}: TasksPageProps) {
  const { isOver, setNodeRef } = useDroppable({ id: TASK_LIST_DROP_ID });
  const [menuTaskId, setMenuTaskId] = useState<Task["id"] | null>(null);

  return (
    <main className="matrix-page">
      <AppHeader currentPage="tasks" />
      <section aria-labelledby="tasks-page-title" className="tasks-page">
        <header className="tasks-page__header">
          <h2 id="tasks-page-title">タスク一覧</h2>
          <p>{tasks.length} tasks</p>
        </header>
        {notice !== null ? (
          <p className="tasks-page__notice" role="status">
            {notice}
          </p>
        ) : null}
        {operationError !== null ? (
          <p className="matrix-page__error tasks-page__error" role="alert">
            {operationError}
          </p>
        ) : null}
        <ul
          ref={setNodeRef}
          aria-label="Task list"
          className={`tasks-page__list${isOver ? " tasks-page__list--drop-target" : ""}`}
        >
          {tasks.map((task) => (
            <TaskListCard
              key={task.id}
              isMenuOpen={menuTaskId === task.id}
              onCloseMenu={() => setMenuTaskId(null)}
              onDeleteTask={onDeleteTask}
              onOpenMenu={() => setMenuTaskId(task.id)}
              onUpdateTaskStatus={onUpdateTaskStatus}
              task={task}
            />
          ))}
        </ul>
      </section>
    </main>
  );
}

type TaskListCardProps = {
  readonly isMenuOpen: boolean;
  readonly onCloseMenu: () => void;
  readonly onDeleteTask: (task: Task) => Promise<boolean>;
  readonly onOpenMenu: () => void;
  readonly onUpdateTaskStatus: (taskId: Task["id"], status: Task["status"]) => Promise<void>;
  readonly task: Task;
};

function TaskListCard({
  isMenuOpen,
  onCloseMenu,
  onDeleteTask,
  onOpenMenu,
  onUpdateTaskStatus,
  task
}: TaskListCardProps) {
  const draggable = useDraggable({ id: taskDropId(task.id) });
  const droppable = useDroppable({ id: taskDropId(task.id) });
  const area = findArea(task.areaId);
  const description =
    task.description.trim().length > 0 ? task.description.trim() : "説明なし";
  const className = [
    "tasks-page__card",
    `tasks-page__card--${task.status}`,
    draggable.isDragging ? "tasks-page__card--dragging" : "",
    droppable.isOver ? "tasks-page__card--drop-target" : ""
  ]
    .filter(Boolean)
    .join(" ");
  const style = {
    transform: CSS.Translate.toString(draggable.transform)
  };
  const availableStatuses = ["active", "done", "skipped"] as const;

  async function handleStatusChange(status: Task["status"]) {
    onCloseMenu();
    await onUpdateTaskStatus(task.id, status);
  }

  return (
    <li
      className={className}
      ref={(node) => {
        draggable.setNodeRef(node);
        droppable.setNodeRef(node);
      }}
      style={style}
    >
      <button
        aria-label={`${area.label} のドラッグハンドル`}
        className="tasks-page__handle"
        type="button"
        {...draggable.listeners}
        {...draggable.attributes}
      >
        <span aria-hidden="true" className="tasks-page__handle-icon">
          ↕
        </span>
        <span className="tasks-page__handle-area">{area.label}</span>
      </button>
      <div className="tasks-page__body">
        <h3 className="tasks-page__card-title">{task.title}</h3>
        <p className="tasks-page__description">{description}</p>
      </div>
      <div className="tasks-page__controls">
        <div className="tasks-page__status">
          <button
            aria-expanded={isMenuOpen}
            aria-haspopup="menu"
            className="tasks-page__button tasks-page__button--status"
            type="button"
            onClick={() => (isMenuOpen ? onCloseMenu() : onOpenMenu())}
          >
            {task.status}
          </button>
          {isMenuOpen ? (
            <div className="tasks-page__status-menu" role="menu" aria-label="status menu">
              {availableStatuses.map((status) => (
                <button
                  key={status}
                  className="tasks-page__status-option"
                  role="menuitem"
                  type="button"
                  onClick={() => void handleStatusChange(status)}
                >
                  {status}
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <a className="tasks-page__button" href={`#/tasks/${task.id}`}>
          詳細
        </a>
        <button
          className="tasks-page__button"
          type="button"
          onClick={() => void onDeleteTask(task)}
        >
          削除
        </button>
      </div>
    </li>
  );
}

type TaskDetailPageProps = {
  readonly operationError: string | null;
  readonly onDeleteTask: (task: Task) => Promise<boolean>;
  readonly onUpdateTaskDetails: (
    taskId: Task["id"],
    details: {
      title: Task["title"];
      description: Task["description"];
      areaId: MatrixAreaId;
      status: Task["status"];
    }
  ) => Promise<string | null>;
  readonly task: Task | null;
};

function TaskDetailPage({
  operationError,
  onDeleteTask,
  onUpdateTaskDetails,
  task
}: TaskDetailPageProps) {
  const [title, setTitle] = useState(task?.title ?? "");
  const [description, setDescription] = useState(task?.description ?? "");
  const [areaId, setAreaId] = useState<MatrixAreaId>(detailAreaId(task));
  const [status, setStatus] = useState<Task["status"]>(task?.status ?? "active");
  const [saveError, setSaveError] = useState<string | null>(null);
  const validationError = validateTaskTitleInput(title);
  const canSave = task !== null && validationError === null;

  useEffect(() => {
    if (task === null) {
      setTitle("");
      setDescription("");
      setAreaId("do");
      setStatus("active");
      setSaveError(null);

      return;
    }

    setTitle(task.title);
    setDescription(task.description);
    setAreaId(detailAreaId(task));
    setStatus(task.status);
    setSaveError(null);
  }, [task]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (task === null) {
      return;
    }

    if (validationError !== null) {
      setSaveError(validationError);

      return;
    }

    const error = await onUpdateTaskDetails(task.id, {
      areaId,
      description,
      status,
      title
    });

    setSaveError(error);
  }

  async function handleDelete() {
    if (task === null) {
      return;
    }

    await onDeleteTask(task);
  }

  return (
    <main className="matrix-page">
      <AppHeader currentPage="tasks" />
      <section aria-labelledby="task-detail-title" className="task-detail-page">
        {task === null ? (
          <>
            <h2 id="task-detail-title">タスクが見つかりませんでした</h2>
            <p>指定された taskId は存在しないか、すでに削除されています。</p>
            <a className="tasks-page__back-link" href="#/tasks">
              タスク一覧へ戻る
            </a>
          </>
        ) : (
          <>
            <header className="task-detail-page__header">
              <h2 id="task-detail-title">タスク詳細</h2>
              <a className="tasks-page__back-link" href="#/tasks">
                タスク一覧へ戻る
              </a>
            </header>
            {operationError !== null ? (
              <p className="matrix-page__error tasks-page__error" role="alert">
                {operationError}
              </p>
            ) : null}
            <form className="task-detail-form" onSubmit={(event) => void handleSubmit(event)}>
              <div className="task-detail-form__grid">
                <label className="task-detail-form__field">
                  title
                  <input
                    name="title"
                    type="text"
                    value={title}
                    onChange={(event) => {
                      setTitle(event.target.value);
                      setSaveError(null);
                    }}
                  />
                </label>
                <label className="task-detail-form__field">
                  area
                  <select
                    name="area"
                    value={areaId}
                    onChange={(event) => {
                      setAreaId(event.target.value as MatrixAreaId);
                      setSaveError(null);
                    }}
                  >
                    {MATRIX_AREAS.map((area) => (
                      <option key={area.id} value={area.id}>
                        {area.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="task-detail-form__field">
                  description
                  <textarea
                    name="description"
                    value={description}
                    onChange={(event) => {
                      setDescription(event.target.value);
                      setSaveError(null);
                    }}
                  />
                </label>
                <div className="task-detail-form__meta">
                  <div>
                    <strong>作成日時</strong>
                    <p>{task.createdAt}</p>
                  </div>
                  <div>
                    <strong>更新日時</strong>
                    <p>{task.updatedAt}</p>
                  </div>
                  <label className="task-detail-form__field">
                    status
                    <select
                      name="status"
                      value={status}
                      onChange={(event) => {
                        setStatus(event.target.value as Task["status"]);
                        setSaveError(null);
                      }}
                    >
                      {(["active", "done", "skipped"] as const).map((candidate) => (
                        <option key={candidate} value={candidate}>
                          {candidate}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </div>
              {validationError !== null ? (
                <p className="task-edit-form__error" role="alert">
                  {validationError}
                </p>
              ) : null}
              {saveError !== null ? (
                <p className="task-edit-form__error" role="alert">
                  {saveError}
                </p>
              ) : null}
              <div className="task-detail-form__actions">
                <button className="tasks-page__button" type="button" onClick={() => void handleDelete()}>
                  削除
                </button>
                <button className="tasks-page__button tasks-page__button--primary" disabled={!canSave} type="submit">
                  保存
                </button>
              </div>
            </form>
          </>
        )}
      </section>
    </main>
  );
}

function detailAreaId(task: Task | null): MatrixAreaId {
  if (task !== null) {
    return normalizeTaskAreaId(task.areaId);
  }

  return "do";
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
    "matrix-workspace__status",
    `matrix-workspace__status--${areaId}`,
    "status-drop-area-shell",
    isOver ? "status-drop-area-shell--drop-target" : ""
  ]
    .filter(Boolean)
    .join(" ");
  const articleClassName = [
    "status-drop-area",
    isOver ? "status-drop-area--drop-target" : ""
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div ref={setNodeRef} className={className}>
      <article className={articleClassName}>
        <h2>{label}</h2>
        <p>0 cards</p>
      </article>
    </div>
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
