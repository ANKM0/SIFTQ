import { INITIAL_AREAS, isMatrixArea } from "../domain/area";
import {
  normalizeTaskTitle,
  statusForArea,
  type Task,
  type TaskId
} from "../domain/task";
import {
  type CreateTaskInput,
  type MoveTaskInput,
  type ReorderTaskInput,
  type TaskRepository
} from "../ports/taskRepository";

type IdGenerator = () => TaskId;

export class InMemoryTaskRepository implements TaskRepository {
  private tasks: Task[];
  private readonly generateId: IdGenerator;

  constructor(options: { tasks?: readonly Task[]; generateId?: IdGenerator } = {}) {
    this.tasks = normalizeOrders([...options.tasks ?? []].sort(compareTasks));
    this.generateId = options.generateId ?? createSequentialIdGenerator();
  }

  async createTask(input: CreateTaskInput): Promise<Task> {
    if (!isMatrixArea(input.areaId)) {
      throw new Error("Tasks can only be created in matrix areas.");
    }

    const title = normalizeTaskTitle(input.title);
    const order = this.tasks.filter((task) => task.areaId === input.areaId).length;
    const task: Task = {
      id: this.generateId(),
      title,
      areaId: input.areaId,
      status: "active",
      order
    };

    this.tasks = normalizeOrders([...this.tasks, task]);

    return task;
  }

  async listTasks(): Promise<Task[]> {
    return [...this.tasks].sort(compareTasks);
  }

  async moveTask(input: MoveTaskInput): Promise<Task> {
    const task = this.findTask(input.taskId);

    if (task.status !== "active" && isMatrixArea(input.toAreaId)) {
      throw new Error("Terminal tasks cannot be restored to matrix areas.");
    }

    const remainingTasks = this.tasks.filter(
      (candidate) => candidate.id !== input.taskId
    );
    const targetStatus = statusForArea(input.toAreaId);
    const movedTask = {
      ...task,
      areaId: input.toAreaId,
      status: targetStatus
    };

    this.tasks = insertTaskAt(remainingTasks, movedTask, input.toAreaId, input.insertAt);

    return this.findTask(input.taskId);
  }

  async reorderTask(input: ReorderTaskInput): Promise<Task> {
    const task = this.findTask(input.taskId);

    if (!isMatrixArea(task.areaId)) {
      throw new Error("Only matrix tasks can be reordered.");
    }

    const remainingTasks = this.tasks.filter(
      (candidate) => candidate.id !== input.taskId
    );

    this.tasks = insertTaskAt(remainingTasks, task, task.areaId, input.toIndex);

    return this.findTask(input.taskId);
  }

  private findTask(taskId: TaskId): Task {
    const task = this.tasks.find((candidate) => candidate.id === taskId);

    if (task === undefined) {
      throw new Error(`Unknown task: ${taskId}`);
    }

    return task;
  }
}

function createSequentialIdGenerator(): IdGenerator {
  let nextId = 1;

  return () => `task-${nextId++}`;
}

function insertTaskAt(
  tasks: readonly Task[],
  task: Task,
  areaId: Task["areaId"],
  insertAt = Number.POSITIVE_INFINITY
): Task[] {
  const orderedTasks = normalizeOrders([...tasks].sort(compareTasks));
  const areaTasks = orderedTasks
    .filter((candidate) => candidate.areaId === areaId)
    .sort(compareTasks);
  const clampedIndex = Math.max(0, Math.min(insertAt, areaTasks.length));
  const beforeTaskId = areaTasks[clampedIndex]?.id;
  const result: Task[] = [];

  for (const candidate of orderedTasks) {
    if (candidate.id === beforeTaskId) {
      result.push(task);
    }

    result.push(candidate);
  }

  if (beforeTaskId === undefined) {
    result.push(task);
  }

  return normalizeOrders(result);
}

function normalizeOrders(tasks: readonly Task[]): Task[] {
  const nextOrderByArea = new Map<Task["areaId"], number>();

  return tasks.map((task) => {
    const nextOrder = nextOrderByArea.get(task.areaId) ?? 0;
    nextOrderByArea.set(task.areaId, nextOrder + 1);

    return { ...task, order: nextOrder };
  });
}

function compareTasks(left: Task, right: Task): number {
  return (
    areaSortIndex(left.areaId) - areaSortIndex(right.areaId) ||
    left.order - right.order
  );
}

function areaSortIndex(areaId: Task["areaId"]): number {
  return INITIAL_AREAS.findIndex((area) => area.id === areaId);
}
