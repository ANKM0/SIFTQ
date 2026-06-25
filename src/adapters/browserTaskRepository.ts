import {
  type AreaId,
  type Task,
  type TaskId
} from "../contracts/task";
import {
  AREA_ORDER,
  compareTasksByAreaOrder,
  isAreaId,
  isMatrixArea,
  isTaskVisibleInMatrix,
  normalizeTaskTitleInput,
  statusForArea,
  validateTaskTitleInput
} from "../domain/taskRules";
import {
  type CreateTaskInput,
  type MoveTaskInput,
  type ReorderTaskInput,
  type TaskRepository,
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
  storageKey = BROWSER_TASK_STORAGE_KEY
): TaskRepository {
  return {
    async createTask(input: CreateTaskInput): Promise<Task> {
      if (!isMatrixArea(input.areaId)) {
        throw new BrowserTaskRepositoryError(
          "VALIDATION",
          "Task can only be created in a matrix area."
        );
      }

      const title = validateTitle(input.title);
      const tasks = loadTasks(storage, storageKey);
      const task = {
        areaId: input.areaId,
        id: idFactory(),
        order: tasksInArea(tasks, input.areaId).length,
        status: "active",
        title
      } satisfies Task;
      const nextTasks = normalizeAllAreas([...tasks, task]);

      saveTasks(storage, storageKey, nextTasks);

      return taskById(nextTasks, task.id);
    },

    async listTasks(): Promise<Task[]> {
      return [...loadTasks(storage, storageKey)].sort(compareTasksByAreaOrder);
    },

    async moveTask(input: MoveTaskInput): Promise<Task> {
      const tasks = loadTasks(storage, storageKey);
      const task = taskById(tasks, input.taskId);

      if (!isTaskVisibleInMatrix(task)) {
        throw new BrowserTaskRepositoryError(
          "VALIDATION",
          "Only active matrix tasks can be moved."
        );
      }

      const withoutTask = normalizeArea(
        tasks.filter((candidate) => candidate.id !== task.id),
        task.areaId
      );
      const movedTask = {
        ...task,
        areaId: input.toAreaId,
        status: statusForArea(input.toAreaId)
      } satisfies Task;
      const targetTasks = tasksInArea(withoutTask, input.toAreaId);
      const insertAt = clamp(input.insertAt ?? targetTasks.length, 0, targetTasks.length);

      targetTasks.splice(insertAt, 0, movedTask);

      const nextTasks = normalizeAreaInCurrentOrder(
        replaceArea(withoutTask, input.toAreaId, targetTasks),
        input.toAreaId
      );

      saveTasks(storage, storageKey, nextTasks);

      return taskById(nextTasks, task.id);
    },

    async reorderTask(input: ReorderTaskInput): Promise<Task> {
      const tasks = loadTasks(storage, storageKey);
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

      areaTasks.splice(insertAt, 0, task);

      const nextTasks = normalizeAreaInCurrentOrder(
        replaceArea(tasks, task.areaId, areaTasks),
        task.areaId
      );

      saveTasks(storage, storageKey, nextTasks);

      return taskById(nextTasks, task.id);
    },

    async updateTaskTitle(input: UpdateTaskTitleInput): Promise<Task> {
      const title = validateTitle(input.title);
      const tasks = loadTasks(storage, storageKey);
      const task = taskById(tasks, input.taskId);
      const nextTasks = tasks.map((candidate) =>
        candidate.id === task.id ? ({ ...candidate, title } satisfies Task) : candidate
      );

      saveTasks(storage, storageKey, nextTasks);

      return taskById(nextTasks, task.id);
    }
  };
}

export const browserTaskRepository: TaskRepository = {
  createTask(input) {
    return getDefaultRepository().createTask(input);
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
  updateTaskTitle(input) {
    return getDefaultRepository().updateTaskTitle(input);
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

function validateTitle(rawTitle: string): string {
  const error = validateTaskTitleInput(rawTitle);

  if (error !== null) {
    throw new BrowserTaskRepositoryError("VALIDATION", error);
  }

  return normalizeTaskTitleInput(rawTitle);
}

function loadTasks(storage: BrowserTaskStorage, storageKey: string): Task[] {
  const rawStore = storage.getItem(storageKey);

  if (rawStore === null) {
    return [];
  }

  try {
    const store = JSON.parse(rawStore) as unknown;

    if (!isBrowserTaskStore(store)) {
      throw new Error("Unexpected browser task store shape.");
    }

    return normalizeAllAreas([...store.tasks]);
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
  const store = {
    tasks: normalizeAllAreas([...tasks]),
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

function isBrowserTaskStore(store: unknown): store is BrowserTaskStore {
  return (
    typeof store === "object" &&
    store !== null &&
    "version" in store &&
    store.version === STORE_VERSION &&
    "tasks" in store &&
    Array.isArray(store.tasks) &&
    store.tasks.every(isStoredTask)
  );
}

function isStoredTask(task: unknown): task is Task {
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

function normalizeAllAreas(tasks: readonly Task[]): Task[] {
  return AREA_ORDER.reduce(
    (normalizedTasks, areaId) => normalizeArea(normalizedTasks, areaId),
    [...tasks]
  ).sort(compareTasksByAreaOrder);
}

function normalizeArea(tasks: readonly Task[], areaId: AreaId): Task[] {
  const normalizedAreaTasks = tasksInArea(tasks, areaId).map((task, order) => ({
    ...task,
    order
  }));

  return replaceArea(tasks, areaId, normalizedAreaTasks).sort(compareTasksByAreaOrder);
}

function normalizeAreaInCurrentOrder(tasks: readonly Task[], areaId: AreaId): Task[] {
  const normalizedAreaTasks = tasks
    .filter((task) => task.areaId === areaId)
    .map((task, order) => ({
      ...task,
      order
    }));

  return replaceArea(tasks, areaId, normalizedAreaTasks).sort(compareTasksByAreaOrder);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
