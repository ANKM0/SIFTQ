import { type Task } from "../domain/task";
import {
  type CreateTaskInput,
  type MoveTaskInput,
  type ReorderTaskInput,
  type TaskRepository
} from "../ports/taskRepository";

export async function createTask(
  repository: TaskRepository,
  input: CreateTaskInput
): Promise<Task> {
  return repository.createTask(input);
}

export async function listTasks(repository: TaskRepository): Promise<Task[]> {
  return repository.listTasks();
}

export async function moveTask(
  repository: TaskRepository,
  input: MoveTaskInput
): Promise<Task> {
  return repository.moveTask(input);
}

export async function reorderTask(
  repository: TaskRepository,
  input: ReorderTaskInput
): Promise<Task> {
  return repository.reorderTask(input);
}
