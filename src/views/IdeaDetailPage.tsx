import type { Idea } from "../idea";

type IdeaDetailData = Idea & { pinned?: boolean };

export function IdeaDetailPage({ idea }: { idea: IdeaDetailData }) {
  return (
    <div class="page page--idea-detail" data-state="normal">
      <form class="idea-detail__form" data-idea-form data-idea-id={idea.id} data-idea-order={idea.order} data-idea-pinned={idea.pinned === true ? "true" : "false"}>
        <header class="idea-detail__header">
          <input class="idea-detail__title" name="title" type="text" value={idea.title} maxlength={256} autocomplete="off" aria-label="Idea title" />
          <button class="idea-detail__pin" type="button" data-idea-pin aria-label="Toggle pin" aria-pressed={idea.pinned === true ? "true" : "false"}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.8v6h2.4v-6H20v-2z" />
            </svg>
          </button>
        </header>
        <textarea class="idea-detail__description" name="description" aria-label="Idea description" rows={1}>{idea.description}</textarea>
        <div class="idea-detail__actions">
          <a class="idea-detail__close" href="/ideas">閉じる</a>
        </div>
      </form>
    </div>
  );
}
