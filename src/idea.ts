import { err, isTaskDescriptionValid, isTaskTitleValid, ok } from "./task";
import type { Result } from "./task";

export type Idea = {
  id: string;
  owner_id: string;
  title: string;
  description: string;
  order: number;
  pinned: boolean;
};

export type IdeaError = {
  code: "INVALID_TITLE" | "INVALID_DESCRIPTION" | "INVALID_ORDER" | "NOT_FOUND" | "CONFLICT";
};

export function isIdeaRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function isIdeaTitleValid(title: string): boolean {
  return isTaskTitleValid(title);
}

export function isIdeaDescriptionValid(description: string): boolean {
  return isTaskDescriptionValid(description);
}

export function isIdeaOrderValid(order: number): boolean {
  return Number.isSafeInteger(order) && order > 0;
}

export function sortIdeas<T extends Idea>(ideas: readonly T[]): T[] {
  return [...ideas].sort((left, right) => left.order - right.order);
}

export function nextIdeaOrder(ideas: readonly Idea[], pinned: boolean): number {
  return ideas.filter((idea) => idea.pinned === pinned).reduce((maximum, idea) => Math.max(maximum, idea.order), 0) + 1;
}

export type IdeaPatch = {
  title?: string;
  description?: string;
  pinned?: boolean;
  order?: number;
};

export function parseIdeaPatch(body: Record<string, unknown>): Result<IdeaPatch, IdeaError> {
  const patch: IdeaPatch = {};

  if (typeof body["title"] === "string") {
    const title = body["title"].trim();
    if (!isIdeaTitleValid(title)) return err({ code: "INVALID_TITLE" });
    patch.title = title;
  }
  if (typeof body["description"] === "string") {
    if (!isIdeaDescriptionValid(body["description"])) return err({ code: "INVALID_DESCRIPTION" });
    patch.description = body["description"];
  }
  if (typeof body["pinned"] === "boolean") {
    patch.pinned = body["pinned"];
  }
  if (body["order"] !== undefined) {
    const order = body["order"];
    if (typeof order !== "number" || !isIdeaOrderValid(order)) return err({ code: "INVALID_ORDER" });
    patch.order = order;
  }

  return ok(patch);
}

export function applyIdeaPatch(idea: Idea, patch: IdeaPatch): Idea {
  return { ...idea, ...patch };
}
