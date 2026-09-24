import type { Idea } from "../idea";
import { sortIdeas } from "../idea";
import { IdeaDetailFields } from "./IdeaDetailFields";

type IdeaCardData = Idea & { pinned?: boolean };

function IdeaDetailModal() {
  return (
    <dialog class="idea-detail-modal" data-idea-modal>
      <form class="idea-detail__form" data-idea-form data-idea-order="" data-idea-pinned="false" data-idea-mode="edit">
        <IdeaDetailFields />
        <div class="idea-detail__actions">
          <button class="idea-detail__close" type="button" data-idea-close>閉じる</button>
        </div>
      </form>
    </dialog>
  );
}

function IdeaCard({ idea }: { idea: IdeaCardData }) {
  return (
    <article
      class="idea-card"
      data-idea-id={idea.id}
      data-idea-order={idea.order}
      data-order={idea.order}
      data-pinned={idea.pinned === true ? "true" : "false"}
      draggable="true"
    >
      <a class="idea-card__link" href={`/ideas/${idea.id}`}>
        <svg
          class="idea-card__pin"
          role="img"
          aria-label={idea.pinned === true ? "Pinned" : "Not pinned"}
          viewBox="0 0 24 24"
        >
          <path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.8v6h2.4v-6H20v-2z" />
        </svg>
        <h2>{idea.title}</h2>
        <p class={idea.description === "" ? "idea-card__description idea-card__description--empty" : "idea-card__description"}>
          {idea.description || "No description yet."}
        </p>
      </a>
      <footer class="idea-card__footer">
        <button type="button" class="idea-card__more" aria-label={`More options for ${idea.title}`}>
          <span aria-hidden="true" />
        </button>
      </footer>
    </article>
  );
}

function IdeaCardGroup({ ideas, group }: { ideas: readonly IdeaCardData[]; group: "pinned" | "unpinned" }) {
  return (
    <div class="ideas-grid" data-idea-group={group}>
      {ideas.map((idea) => <IdeaCard key={`${idea.order}-${idea.title}`} idea={idea} />)}
    </div>
  );
}

function IdeaComposer() {
  return (
    <div class="ideas-composer" data-idea-composer data-idea-composer-open="false">
      <button class="ideas-composer__trigger" type="button" data-idea-composer-trigger aria-expanded="false">
        <span>メモを入力...</span>
        <span class="ideas-composer__line" aria-hidden="true" />
      </button>
      <div class="ideas-composer__editor" data-idea-composer-editor hidden>
        <input class="ideas-composer__title" name="title" type="text" maxlength={256} autocomplete="off" placeholder="タイトル" aria-label="Idea title" />
        <textarea class="ideas-composer__description" name="description" placeholder="メモを入力..." aria-label="Idea description" rows={1}></textarea>
        <div class="ideas-composer__actions">
          <button class="ideas-composer__close" type="button" data-idea-composer-close>キャンセル</button>
        </div>
      </div>
    </div>
  );
}

export function IdeasPage({ ideas: sourceIdeas }: { ideas: readonly IdeaCardData[] }) {
  const ideas = sortIdeas(sourceIdeas).sort(
    (left, right) => Number(right.pinned === true) - Number(left.pinned === true),
  );
  const pinnedIdeas = ideas.filter((idea) => idea.pinned === true);
  const unpinnedIdeas = ideas.filter((idea) => idea.pinned !== true);

  return (
    <div class="page page--ideas" data-state="normal">
      <IdeaComposer />
      {ideas.length === 0 && (
        <div class="ideas-empty" data-ideas-empty>
          <h2>No ideas yet</h2>
          <p class="muted">Ideas will appear here.</p>
        </div>
      )}
      <IdeaCardGroup ideas={pinnedIdeas} group="pinned" />
      <div class="ideas-group-gap" data-idea-group-gap aria-hidden="true" hidden={unpinnedIdeas.length === 0} />
      <IdeaCardGroup ideas={unpinnedIdeas} group="unpinned" />
      <IdeaDetailModal />
     </div>
  );
}
