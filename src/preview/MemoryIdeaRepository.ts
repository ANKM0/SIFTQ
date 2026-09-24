import { err, ok } from "../task";
import type { Result } from "../task";
import type { Idea } from "../idea";
import type { IdeaOrderUpdate, IdeaRepository, IdeaRepositoryError } from "../repository/idea-repository";

export function createMemoryIdeaRepository(initialIdeas: readonly Idea[] = []): IdeaRepository {
  const ideas = new Map(initialIdeas.map((idea) => [idea.id, idea]));

  async function list(owner_id: string): Promise<Result<Idea[], IdeaRepositoryError>> {
    return ok([...ideas.values()].filter((idea) => idea.owner_id === owner_id));
  }

  async function find(id: string, owner_id: string): Promise<Result<Idea | undefined, IdeaRepositoryError>> {
    const idea = ideas.get(id);
    return ok(idea?.owner_id === owner_id ? idea : undefined);
  }

  async function insert(idea: Idea): Promise<Result<Idea, IdeaRepositoryError>> {
    ideas.set(idea.id, idea);
    return ok(idea);
  }

  async function update(idea: Idea): Promise<Result<Idea, IdeaRepositoryError>> {
    const current = ideas.get(idea.id);
    if (!current || current.owner_id !== idea.owner_id) return err({ code: "NOT_FOUND" });
    ideas.set(idea.id, idea);
    return ok(idea);
  }

  async function remove(id: string, owner_id: string): Promise<Result<null, IdeaRepositoryError>> {
    const current = ideas.get(id);
    if (!current || current.owner_id !== owner_id) return err({ code: "NOT_FOUND" });
    ideas.delete(id);
    return ok(null);
  }

  async function move(
    owner_id: string,
    updates: readonly IdeaOrderUpdate[],
  ): Promise<Result<Idea[], IdeaRepositoryError>> {
    const current = updates.map((update) => ideas.get(update.id));
    if (current.some((idea) => idea === undefined || idea.owner_id !== owner_id)) return err({ code: "CONFLICT" });
    const changed: Idea[] = [];
    for (const [index, idea] of current.entries()) {
      if (idea === undefined) return err({ code: "CONFLICT" });
      changed.push({ ...idea, order: updates[index]?.order ?? idea.order });
    }
    changed.forEach((idea) => ideas.set(idea.id, idea));
    return ok(changed);
  }

  return { list, find, insert, update, remove, move };
}
