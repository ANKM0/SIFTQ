import {
  type CommandErrorDto,
  type CreateTaskRequest,
  type MoveTaskRequest,
  type ReorderTaskRequest,
  type StorageHealthDto,
  type Task,
  type TaskDto,
  type UpdateTaskTitleRequest
} from "../contracts/task";
import {
  type CreateTaskInput,
  type MoveTaskInput,
  type ReorderTaskInput,
  type TaskRepository,
  type UpdateTaskTitleInput
} from "../ports/taskRepository";
import { tauriInvoke, type Invoke } from "./tauriInvoke";

export class TauriCommandError extends Error {
  readonly code: string;

  constructor(error: CommandErrorDto) {
    super(error.message);
    this.name = "TauriCommandError";
    this.code = error.code;
  }
}

export function createTauriTaskRepository(invoke: Invoke): TaskRepository {
  return {
    async createTask(input: CreateTaskInput): Promise<Task> {
      const request: CreateTaskRequest = {
        areaId: input.areaId,
        title: input.title.trim()
      };

      return invokeTask("create_task", { input: request }, invoke);
    },

    async listTasks(): Promise<Task[]> {
      const tasks = await invokeCommand<TaskDto[]>("list_tasks", undefined, invoke);

      return tasks.map(toTask);
    },

    async moveTask(input: MoveTaskInput): Promise<Task> {
      const request: MoveTaskRequest = {
        taskId: input.taskId,
        toAreaId: input.toAreaId,
        ...(input.insertAt === undefined ? {} : { insertAt: input.insertAt })
      };

      return invokeTask("move_task", { input: request }, invoke);
    },

    async reorderTask(input: ReorderTaskInput): Promise<Task> {
      const request: ReorderTaskRequest = {
        taskId: input.taskId,
        toIndex: input.toIndex
      };

      return invokeTask("reorder_task", { input: request }, invoke);
    },

    async updateTaskTitle(input: UpdateTaskTitleInput): Promise<Task> {
      const request: UpdateTaskTitleRequest = {
        taskId: input.taskId,
        title: input.title.trim()
      };

      return invokeTask("update_task_title", { input: request }, invoke);
    }
  };
}

export const tauriTaskRepository = createTauriTaskRepository(tauriInvoke);

export async function getStorageHealth(
  invoke: Invoke = tauriInvoke
): Promise<StorageHealthDto> {
  return invokeCommand("get_storage_health", undefined, invoke);
}

async function invokeTask(
  command: string,
  args: Record<string, unknown>,
  invoke: Invoke
): Promise<Task> {
  const task = await invokeCommand<TaskDto>(command, args, invoke);

  return toTask(task);
}

async function invokeCommand<T>(
  command: string,
  args: Record<string, unknown> | undefined,
  invoke: Invoke
): Promise<T> {
  try {
    return await invoke<T>(command, args);
  } catch (error) {
    throw normalizeCommandError(error);
  }
}

function normalizeCommandError(error: unknown): Error {
  if (isCommandErrorDto(error)) {
    return new TauriCommandError(error);
  }

  if (error instanceof Error) {
    return error;
  }

  return new TauriCommandError({
    code: "INTERNAL",
    message: "Tauri command failed."
  });
}

function isCommandErrorDto(error: unknown): error is CommandErrorDto {
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    "message" in error &&
    typeof error.code === "string" &&
    typeof error.message === "string"
  );
}

function toTask(task: TaskDto): Task {
  return {
    areaId: task.areaId,
    id: task.id,
    order: task.order,
    status: task.status,
    title: task.title
  };
}
