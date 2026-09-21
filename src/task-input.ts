import { isTaskArea, isTaskTitleValid } from "./task";
import type { Task } from "./task";

export type ParsedBody = Record<string, unknown>;

export function parseVersion(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1) return null;
  return value;
}

function parseTaskOrder(value: unknown): number | null {
  if (typeof value !== "string" || value === "") return null;
  const order = Number(value);
  if (!Number.isInteger(order) || order < 0) return null;
  return order;
}

export function parseTaskVersion(value: unknown): number | null {
  if (typeof value !== "string" || value === "") return null;
  const version = Number(value);
  if (!Number.isInteger(version) || version < 1) return null;
  return version;
}

export function parseTaskArea(value: unknown): Task["area"] | null {
  const area = parseTaskOrder(value);
  return area !== null && isTaskArea(area) ? area : null;
}

export function readTaskFields(body: ParsedBody): {
  title: string;
  description: string;
} {
  const title = typeof body["title"] === "string" ? body["title"].trim() : "";
  const description = typeof body["description"] === "string" ? body["description"] : "";
  return { title, description };
}

export function isInvalidTaskTitle(title: string): boolean {
  return !isTaskTitleValid(title);
}
