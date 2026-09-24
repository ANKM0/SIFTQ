export type Idea = {
  title: string;
  description: string;
  order: number;
};

export function sortIdeas<T extends Idea>(ideas: readonly T[]): T[] {
  return [...ideas].sort((left, right) => left.order - right.order);
}
