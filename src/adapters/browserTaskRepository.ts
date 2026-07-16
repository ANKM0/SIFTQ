import {
  type MatrixAreaId,
  type AreaId,
  type Task,
  type TaskId,
  type TaskStatus
} from "../contracts/task";
import {
  AREA_ORDER,
  compareTasksByAreaOrder,
  compareTasksByListOrder,
  isAreaId,
  isMatrixArea,
  isTaskVisibleInMatrix,
  normalizeTaskAreaId,
  normalizeTaskTitleInput,
  statusForArea,
  validateTaskTitleInput
} from "../domain/taskRules";
import {
  type BulkDeleteTasksInput,
  type CreateTaskInput,
  type DeleteTaskInput,
  type MoveTaskInput,
  type ReorderTaskInput,
  type ReorderTaskListInput,
  type TaskRepository,
  type UpdateTaskDetailsInput,
  type UpdateTaskStatusInput,
  type UpdateTaskTitleInput
} from "../ports/taskRepository";

export const BROWSER_TASK_STORAGE_KEY = "siftq.tasks.v1";
const STORE_VERSION = 1;

type BrowserTaskStore = {
  readonly version: typeof STORE_VERSION;
  readonly tasks: readonly Task[];
};

type BrowserTaskStorage = Pick<Storage, "getItem" | "setItem">;

type TaskIdFactory = () => TaskId;
type TimestampFactory = () => string;
type RawBrowserTaskStore = {
  readonly version: typeof STORE_VERSION;
  readonly tasks: readonly unknown[];
};
type LoadedTasksResult = {
  readonly tasks: Task[];
  readonly didMigrate: boolean;
};
type StoredTaskWithOptionalMetadata = Pick<
  Task,
  "id" | "title" | "areaId" | "status" | "order"
> &
  Partial<Pick<Task, "description" | "createdAt" | "updatedAt" | "listOrder">>;

export class BrowserTaskRepositoryError extends Error {
  readonly code: "VALIDATION" | "NOT_FOUND" | "STORAGE";

  constructor(code: BrowserTaskRepositoryError["code"], message: string) {
    super(message);
    this.name = "BrowserTaskRepositoryError";
    this.code = code;
  }
}

export function createBrowserTaskRepository(
  storage: BrowserTaskStorage = defaultBrowserStorage(),
  idFactory: TaskIdFactory = createTaskId,
  storageKey = BROWSER_TASK_STORAGE_KEY,
  nowFactory: TimestampFactory = createTimestamp
): TaskRepository {
  const loadPersistedTasks = (): Task[] => {
    const { didMigrate, tasks } = loadTasks(storage, storageKey);

    if (didMigrate) {
      saveTasks(storage, storageKey, tasks);
    }

    return tasks;
  };

  return {
    async bulkDeleteTasks(input: BulkDeleteTasksInput): Promise<void> {
      const tasks = loadPersistedTasks();
      const deletedTaskIds = new Set(input.taskIds.map((taskId) => taskById(tasks, taskId).id));
      const nextTasks = deleteTasks(tasks, deletedTaskIds, nowFactory());

      saveTasks(storage, storageKey, nextTasks);
    },

    async createTask(input: CreateTaskInput): Promise<Task> {
      if (!isMatrixArea(input.areaId)) {
        throw new BrowserTaskRepositoryError(
          "VALIDATION",
          "Task can only be created in a matrix area."
        );
      }

      const title = validateTitle(input.title);
      const tasks = loadPersistedTasks();
      const timestamp = nowFactory();
      const task = {
        areaId: input.areaId,
        createdAt: timestamp,
        description: "",
        id: idFactory(),
        listOrder: nextListOrder(tasks),
        order: visibleTasksInArea(tasks, input.areaId).length,
        status: "active",
        title,
        updatedAt: timestamp
      } satisfies Task;
      const nextTasks = normalizeAllAreas([...tasks, task]);

      saveTasks(storage, storageKey, nextTasks);

      return taskById(nextTasks, task.id);
    },

    async deleteTask(input: DeleteTaskInput): Promise<void> {
      const tasks = loadPersistedTasks();
      const task = taskById(tasks, input.taskId);
      const nextTasks = deleteTasks(tasks, new Set([task.id]), nowFactory());

      saveTasks(storage, storageKey, nextTasks);
    },

    async listTasks(): Promise<Task[]> {
      return [...loadPersistedTasks()].sort(compareTasksByListOrder);
    },

    async moveTask(input: MoveTaskInput): Promise<Task> {
      const tasks = loadPersistedTasks();
      const task = taskById(tasks, input.taskId);

      if (!isTaskVisibleInMatrix(task) || !isMatrixArea(task.areaId)) {
        throw new BrowserTaskRepositoryError(
          "VALIDATION",
          "Only active matrix tasks can be moved."
        );
      }
      const sourceAreaId: MatrixAreaId = task.areaId;

      const withoutTask = normalizeArea(
        tasks.filter((candidate) => candidate.id !== task.id),
        sourceAreaId
      );
      const nextStatus = statusForArea(input.toAreaId);
      const targetAreaId = input.toAreaId;
      const targetVisibleTasks =
        nextStatus === "active" && isMatrixArea(targetAreaId)
          ? visibleTasksInArea(withoutTask, targetAreaId)
          : [];
      const movedTask = {
        ...task,
        areaId: nextStatus === "active" ? targetAreaId : sourceAreaId,
        order:
          nextStatus === "active"
            ? clamp(
                input.insertAt ?? targetVisibleTasks.length,
                0,
                targetVisibleTasks.length
              )
            : visibleTasksInArea(withoutTask, sourceAreaId).length,
        status: nextStatus,
        updatedAt: nowFactory()
      } satisfies Task;
      const nextTasks =
        nextStatus === "active" && isMatrixArea(targetAreaId)
          ? insertVisibleTaskIntoArea(
              withoutTask,
              targetAreaId,
              movedTask,
              movedTask.order
            )
          : upsertTask(withoutTask, movedTask);

      saveTasks(storage, storageKey, nextTasks);

      return taskById(nextTasks, task.id);
    },

    async reorderTask(input: ReorderTaskInput): Promise<Task> {
      const tasks = loadPersistedTasks();
      const task = taskById(tasks, input.taskId);

      if (!isTaskVisibleInMatrix(task)) {
        throw new BrowserTaskRepositoryError(
          "VALIDATION",
          "Only active matrix tasks can be reordered."
        );
      }

      const areaTasks = tasksInArea(tasks, task.areaId).filter(
        (candidate) => candidate.id !== task.id
      );
      const insertAt = clamp(input.toIndex, 0, areaTasks.length);

      areaTasks.splice(insertAt, 0, {
        ...task,
        updatedAt: nowFactory()
      } satisfies Task);

      const nextTasks = normalizeAreaInCurrentOrder(
        replaceArea(tasks, task.areaId, areaTasks),
        task.areaId
      );

      saveTasks(storage, storageKey, nextTasks);

      return taskById(nextTasks, task.id);
    },

    async updateTaskTitle(input: UpdateTaskTitleInput): Promise<Task> {
      const title = validateTitle(input.title);
      const tasks = loadPersistedTasks();
      const task = taskById(tasks, input.taskId);
      const updatedAt = nowFactory();
      const nextTasks = tasks.map((candidate) =>
        candidate.id === task.id
          ? ({ ...candidate, title, updatedAt } satisfies Task)
          : candidate
      );

      saveTasks(storage, storageKey, nextTasks);

      return taskById(nextTasks, task.id);
    },

    async reorderTaskList(input: ReorderTaskListInput): Promise<Task> {
      const tasks = loadPersistedTasks();
      const task = taskById(tasks, input.taskId);
      const orderedTasks = [...tasks].sort(compareTasksByListOrder);
      const fromIndex = orderedTasks.findIndex((candidate) => candidate.id === task.id);
      const [movedTask] = orderedTasks.splice(fromIndex, 1);
      const insertAt = clamp(input.toIndex, 0, orderedTasks.length);

      orderedTasks.splice(insertAt, 0, movedTask);

      const updatedAt = nowFactory();
      const nextTasks = orderedTasks.map((candidate, index) =>
        candidate.listOrder === index
          ? candidate
          : ({ ...candidate, listOrder: index, updatedAt } satisfies Task)
      );

      saveTasks(storage, storageKey, nextTasks);

      return taskById(nextTasks, task.id);
    },

    async updateTaskStatus(input: UpdateTaskStatusInput): Promise<Task> {
      const tasks = loadPersistedTasks();
      const task = taskById(tasks, input.taskId);
      const nextTasks = updateTaskStatus(tasks, task, input.status, nowFactory());

      saveTasks(storage, storageKey, nextTasks);

      return taskById(nextTasks, task.id);
    },

    async updateTaskDetails(input: UpdateTaskDetailsInput): Promise<Task> {
      const title = validateTitle(input.title);
      const tasks = loadPersistedTasks();
      const task = taskById(tasks, input.taskId);
      const updatedAt = nowFactory();
      const nextTasks = updateTaskDetails(tasks, task, {
        ...input,
        title
      }, updatedAt);

      saveTasks(storage, storageKey, nextTasks);

      return taskById(nextTasks, task.id);
    }
  };
}

export const browserTaskRepository: TaskRepository = {
  bulkDeleteTasks(input) {
    return getDefaultRepository().bulkDeleteTasks(input);
  },
  createTask(input) {
    return getDefaultRepository().createTask(input);
  },
  deleteTask(input) {
    return getDefaultRepository().deleteTask(input);
  },
  listTasks() {
    return getDefaultRepository().listTasks();
  },
  moveTask(input) {
    return getDefaultRepository().moveTask(input);
  },
  reorderTask(input) {
    return getDefaultRepository().reorderTask(input);
  },
  reorderTaskList(input) {
    return getDefaultRepository().reorderTaskList(input);
  },
  updateTaskTitle(input) {
    return getDefaultRepository().updateTaskTitle(input);
  },
  updateTaskStatus(input) {
    return getDefaultRepository().updateTaskStatus(input);
  },
  updateTaskDetails(input) {
    return getDefaultRepository().updateTaskDetails(input);
  }
};

function getDefaultRepository(): TaskRepository {
  return createBrowserTaskRepository();
}

function defaultBrowserStorage(): BrowserTaskStorage {
  if (typeof window === "undefined" || window.localStorage === undefined) {
    throw new BrowserTaskRepositoryError(
      "STORAGE",
      "Browser local storage is not available."
    );
  }

  return window.localStorage;
}

function createTaskId(): TaskId {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `task-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

function createTimestamp(): string {
  return new Date().toISOString();
}

function validateTitle(rawTitle: string): string {
  const error = validateTaskTitleInput(rawTitle);

  if (error !== null) {
    throw new BrowserTaskRepositoryError("VALIDATION", error);
  }

  return normalizeTaskTitleInput(rawTitle);
}

function loadTasks(storage: BrowserTaskStorage, storageKey: string): LoadedTasksResult {
  const rawStore = storage.getItem(storageKey);

  if (rawStore === null) {
    return { didMigrate: false, tasks: [] };
  }

  try {
    const store = JSON.parse(rawStore) as unknown;

    if (!isBrowserTaskStore(store)) {
      throw new Error("Unexpected browser task store shape.");
    }

    const migratedTasks = migrateStoredTasks(store.tasks);

    return {
      didMigrate: migratedTasks.didMigrate,
      tasks: normalizeAllAreas(migratedTasks.tasks)
    };
  } catch (error) {
    throw new BrowserTaskRepositoryError(
      "STORAGE",
      error instanceof Error ? error.message : "Browser task store could not be read."
    );
  }
}

function saveTasks(
  storage: BrowserTaskStorage,
  storageKey: string,
  tasks: readonly Task[]
) {
  const normalizedTasks = normalizeAllAreas([...tasks]).sort(compareTasksByListOrder);
  const store = {
    tasks: normalizedTasks,
    version: STORE_VERSION
  } satisfies BrowserTaskStore;

  try {
    storage.setItem(storageKey, JSON.stringify(store));
  } catch (error) {
    throw new BrowserTaskRepositoryError(
      "STORAGE",
      error instanceof Error ? error.message : "Browser task store could not be written."
    );
  }
}

function isBrowserTaskStore(store: unknown): store is RawBrowserTaskStore {
  return (
    typeof store === "object" &&
    store !== null &&
    "version" in store &&
    store.version === STORE_VERSION &&
    "tasks" in store &&
    Array.isArray(store.tasks)
  );
}

function isStoredTask(task: unknown): task is StoredTaskWithOptionalMetadata {
  return (
    typeof task === "object" &&
    task !== null &&
    "id" in task &&
    typeof task.id === "string" &&
    "title" in task &&
    typeof task.title === "string" &&
    "areaId" in task &&
    typeof task.areaId === "string" &&
    isAreaId(task.areaId) &&
    "status" in task &&
    (task.status === "active" || task.status === "done" || task.status === "skipped") &&
    "order" in task &&
    typeof task.order === "number" &&
    Number.isInteger(task.order) &&
    task.order >= 0
  );
}

function migrateStoredTasks(tasks: readonly unknown[]): LoadedTasksResult {
  const parsedTasks = tasks.map((task) => {
    if (!isStoredTask(task)) {
      throw new Error("Unexpected browser task store shape.");
    }

    return task;
  });
  const fallbackCreatedAtById = new Map(
    parsedTasks.map((task, index) => [task.id, legacyTimestampFor(index)] as const)
  );
  let didMigrate = false;

  const tasksWithMetadata = parsedTasks.map((task) => {
    const areaId = normalizeTaskAreaId(task.areaId);
    const description = typeof task.description === "string" ? task.description : "";
    const createdAt = isTimestamp(task.createdAt)
      ? task.createdAt
      : fallbackCreatedAtById.get(task.id) ?? legacyTimestampFor(0);
    const updatedAt = isTimestamp(task.updatedAt) ? task.updatedAt : createdAt;

    if (
      areaId !== task.areaId ||
      description !== task.description ||
      createdAt !== task.createdAt ||
      updatedAt !== task.updatedAt
    ) {
      didMigrate = true;
    }

    return {
      ...task,
      areaId,
      createdAt,
      description,
      updatedAt
    } satisfies Omit<Task, "listOrder">;
  });

  const nextListOrders = deriveListOrders(tasksWithMetadata);

  return {
    didMigrate:
      didMigrate ||
      tasksWithMetadata.some((task) => task.listOrder !== nextListOrders.get(task.id)),
    tasks: tasksWithMetadata.map((task) => ({
      ...task,
      listOrder: nextListOrders.get(task.id) ?? 0
    }))
  };
}

function deriveListOrders(
  tasks: readonly (Omit<Task, "listOrder"> & Partial<Pick<Task, "listOrder">>)[]
): Map<TaskId, number> {
  const hasDistinctListOrders =
    tasks.every(
      (task) =>
        typeof task.listOrder === "number" &&
        Number.isInteger(task.listOrder) &&
        task.listOrder >= 0
    ) &&
    new Set(tasks.map((task) => task.listOrder)).size === tasks.length;

  const orderedTasks = hasDistinctListOrders
    ? [...tasks].sort(
        (left, right) =>
          (left.listOrder ?? 0) - (right.listOrder ?? 0) || left.id.localeCompare(right.id)
      )
    : [...tasks].sort(
        (left, right) =>
          left.createdAt.localeCompare(right.createdAt) ||
          compareByAreaAndOrder(left, right) ||
          left.id.localeCompare(right.id)
      );

  return new Map(orderedTasks.map((task, index) => [task.id, index] as const));
}

function isTimestamp(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && !Number.isNaN(Date.parse(value));
}

function legacyTimestampFor(index: number): string {
  return new Date(index).toISOString();
}

function taskById(tasks: readonly Task[], taskId: TaskId): Task {
  const task = tasks.find((candidate) => candidate.id === taskId);

  if (task === undefined) {
    throw new BrowserTaskRepositoryError("NOT_FOUND", "Task was not found.");
  }

  return task;
}

function tasksInArea(tasks: readonly Task[], areaId: AreaId): Task[] {
  return [...tasks]
    .filter((task) => task.areaId === areaId)
    .sort((left, right) => left.order - right.order || left.id.localeCompare(right.id));
}

function visibleTasksInArea(tasks: readonly Task[], areaId: MatrixAreaId): Task[] {
  return tasksInArea(tasks, areaId).filter(isTaskVisibleInMatrix);
}

function replaceArea(
  tasks: readonly Task[],
  areaId: AreaId,
  areaTasks: readonly Task[]
): Task[] {
  return [
    ...tasks.filter((task) => task.areaId !== areaId),
    ...areaTasks
  ];
}

function upsertTask(tasks: readonly Task[], nextTask: Task): Task[] {
  const didReplace = tasks.some((task) => task.id === nextTask.id);

  if (!didReplace) {
    return [...tasks, nextTask];
  }

  return tasks.map((task) => (task.id === nextTask.id ? nextTask : task));
}

function normalizeAllAreas(tasks: readonly Task[]): Task[] {
  return AREA_ORDER.reduce(
    (normalizedTasks, areaId) => normalizeArea(normalizedTasks, areaId),
    [...tasks]
  ).sort(compareTasksByAreaOrder);
}

function normalizeArea(tasks: readonly Task[], areaId: AreaId): Task[] {
  const normalizedAreaTasks = normalizeVisibleAreaTasks(tasksInArea(tasks, areaId));

  return replaceArea(tasks, areaId, normalizedAreaTasks).sort(compareTasksByAreaOrder);
}

function normalizeAreaInCurrentOrder(tasks: readonly Task[], areaId: AreaId): Task[] {
  const normalizedAreaTasks = normalizeVisibleAreaTasks(
    tasks.filter((task) => task.areaId === areaId)
  );

  return replaceArea(tasks, areaId, normalizedAreaTasks).sort(compareTasksByAreaOrder);
}

function normalizeVisibleAreaTasks(tasks: readonly Task[]): Task[] {
  let nextOrder = 0;

  return tasks.map((task) =>
    isTaskVisibleInMatrix(task) ? { ...task, order: nextOrder++ } : task
  );
}

function insertVisibleTaskIntoArea(
  tasks: readonly Task[],
  areaId: MatrixAreaId,
  task: Task,
  insertAt: number
): Task[] {
  const areaTasks = tasks.filter((candidate) => candidate.areaId === areaId);
  const visibleTasks = areaTasks.filter(isTaskVisibleInMatrix);
  const hiddenTasks = areaTasks.filter((candidate) => !isTaskVisibleInMatrix(candidate));
  const nextVisibleTasks = [...visibleTasks];

  nextVisibleTasks.splice(insertAt, 0, task);

  return replaceArea(
    tasks,
    areaId,
    normalizeVisibleAreaTasks([...nextVisibleTasks, ...hiddenTasks])
  ).sort(compareTasksByAreaOrder);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function nextListOrder(tasks: readonly Task[]): number {
  return tasks.reduce((maxOrder, task) => Math.max(maxOrder, task.listOrder), -1) + 1;
}

function deleteTasks(
  tasks: readonly Task[],
  deletedTaskIds: ReadonlySet<TaskId>,
  updatedAt: string
): Task[] {
  if (deletedTaskIds.size === 0) {
    return [...tasks];
  }

  const remainingTasks = tasks.filter((task) => !deletedTaskIds.has(task.id));
  const normalizedTasks = normalizeAllAreas(remainingTasks);
  const orderedTasks = [...normalizedTasks].sort(compareTasksByListOrder);

  return orderedTasks.map((task, listOrder) =>
    task.listOrder === listOrder
      ? task
      : ({ ...task, listOrder, updatedAt } satisfies Task)
  );
}

function updateTaskStatus(
  tasks: readonly Task[],
  task: Task,
  status: TaskStatus,
  updatedAt: string
): Task[] {
  if (task.status === status) {
    return [...tasks];
  }

  if (status === "active" && !isMatrixArea(task.areaId)) {
    throw new BrowserTaskRepositoryError(
      "VALIDATION",
      "Active tasks must belong to a matrix area."
    );
  }

  if (task.status === "active" && status !== "active" && isMatrixArea(task.areaId)) {
    const sourceAreaId = task.areaId;
    const withoutTask = normalizeArea(
      tasks.filter((candidate) => candidate.id !== task.id),
      sourceAreaId
    );
    const hiddenTask = {
      ...task,
      order: visibleTasksInArea(withoutTask, sourceAreaId).length,
      status,
      updatedAt
    } satisfies Task;

    return upsertTask(withoutTask, hiddenTask);
  }

  if (task.status !== "active" && status === "active" && isMatrixArea(task.areaId)) {
    const restoredAreaId = task.areaId;
    const restoredTask = {
      ...task,
      order: visibleTasksInArea(
        tasks.filter((candidate) => candidate.id !== task.id),
        restoredAreaId
      ).length,
      status,
      updatedAt
    } satisfies Task;

    return normalizeAreaInCurrentOrder(upsertTask(tasks, restoredTask), restoredAreaId);
  }

  return upsertTask(tasks, { ...task, status, updatedAt });
}

function updateTaskDetails(
  tasks: readonly Task[],
  task: Task,
  input: UpdateTaskDetailsInput,
  updatedAt: string
): Task[] {
  const previousAreaId = task.areaId;
  const nextAreaId = input.areaId;
  const nextStatus = input.status;

  if (!isMatrixArea(nextAreaId)) {
    throw new BrowserTaskRepositoryError(
      "VALIDATION",
      "Task detail area must belong to a matrix area."
    );
  }

  if (previousAreaId === nextAreaId && task.status === nextStatus) {
    return upsertTask(tasks, {
      ...task,
      description: input.description,
      title: input.title,
      updatedAt
    });
  }

  const withoutTask = tasks.filter((candidate) => candidate.id !== task.id);
  const normalizedWithoutPreviousArea =
    isMatrixArea(previousAreaId) && task.status === "active"
      ? normalizeArea(withoutTask, previousAreaId)
      : withoutTask;
  const nextOrder =
    isMatrixArea(nextAreaId) &&
    nextStatus === "active"
      ? visibleTasksInArea(normalizedWithoutPreviousArea, nextAreaId).length
      : tasksInArea(normalizedWithoutPreviousArea, nextAreaId).length;
  const nextTask = {
    ...task,
    areaId: nextAreaId,
    description: input.description,
    order: nextOrder,
    status: nextStatus,
    title: input.title,
    updatedAt
  } satisfies Task;
  const withUpdatedTask = upsertTask(normalizedWithoutPreviousArea, nextTask);

  if (nextStatus === "active") {
    return normalizeAreaInCurrentOrder(withUpdatedTask, nextAreaId);
  }

  return withUpdatedTask;
}

function compareByAreaAndOrder(
  left: Pick<Task, "areaId" | "order" | "id">,
  right: Pick<Task, "areaId" | "order" | "id">
): number {
  return (
    AREA_ORDER.indexOf(left.areaId) - AREA_ORDER.indexOf(right.areaId) ||
    left.order - right.order ||
    left.id.localeCompare(right.id)
  );
}
