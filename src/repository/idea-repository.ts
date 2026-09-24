import type { Idea, IdeaError } from "../idea";
import type { Result } from "../task";

export type IdeaRepositoryError = IdeaError;

export type IdeaOrderUpdate = {
  id: string;
  order: number;
};

export interface IdeaRepository {
  list(owner_id: string): Promise<Result<Idea[], IdeaRepositoryError>>;
  find(id: string, owner_id: string): Promise<Result<Idea | undefined, IdeaRepositoryError>>;
  insert(idea: Idea): Promise<Result<Idea, IdeaRepositoryError>>;
  update(idea: Idea): Promise<Result<Idea, IdeaRepositoryError>>;
  remove(id: string, owner_id: string): Promise<Result<null, IdeaRepositoryError>>;
  move(owner_id: string, updates: readonly IdeaOrderUpdate[]): Promise<Result<Idea[], IdeaRepositoryError>>;
}
