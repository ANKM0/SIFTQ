import type { Task } from "../../src/task";

export function taskFixture(overrides: Partial<Task> = {}): Task {
  return {
    id: "task-1",
    owner_id: "owner-1",
    title: "seed task",
    description: "",
    status: "do",
    area: 1,
    order: 1,
    version: 1,
    created_at: "2026-01-01T00:00:00.000Z",
    updated_at: "2026-01-01T00:00:00.000Z",
    ...overrides,
  };
}
