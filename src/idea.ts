import { isTaskDescriptionValid, isTaskTitleValid } from "./task";

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
