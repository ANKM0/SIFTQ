import type { Idea } from "../idea";
import { IdeaDetailFields } from "./IdeaDetailFields";

type IdeaDetailData = Idea & { pinned?: boolean };

export function IdeaDetailPage({ idea }: { idea: IdeaDetailData }) {
  return (
    <div class="page page--idea-detail" data-state="normal">
      <form class="idea-detail__form" data-idea-form data-idea-id={idea.id} data-idea-order={idea.order} data-idea-pinned={idea.pinned === true ? "true" : "false"}>
        <IdeaDetailFields title={idea.title} description={idea.description} pinned={idea.pinned === true} />
        <div class="idea-detail__actions">
          <a class="idea-detail__close" href="/ideas">閉じる</a>
        </div>
      </form>
    </div>
  );
}
