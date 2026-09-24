import { splitDescription } from "../description";

export function IdeaDetailFields({
  title,
  description = "",
  pinned = false,
}: {
  title?: string;
  description?: string;
  pinned?: boolean;
}) {
  return (
    <>
      <header class="idea-detail__header">
        <input class="idea-detail__title" name="title" type="text" value={title} maxlength={256} autocomplete="off" aria-label="Idea title" />
        <button class="idea-detail__pin" type="button" data-idea-pin aria-label="Toggle pin" aria-pressed={pinned ? "true" : "false"}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.8v6h2.4v-6H20v-2z" />
          </svg>
        </button>
      </header>
      <div
        class="idea-detail__description"
        contenteditable={true}
        data-description-editor
        role="textbox"
        aria-multiline="true"
        aria-label="Idea description"
      >
        {splitDescription(description).map((segment, index) =>
          segment.href ? (
            <a key={index} href={segment.href}>
              {segment.text}
            </a>
          ) : (
            segment.text
          ),
        )}
      </div>
      <textarea name="description" data-description-value hidden>
        {description}
      </textarea>
    </>
  );
}
