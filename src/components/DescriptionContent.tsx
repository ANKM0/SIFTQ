import type { JSX } from "hono/jsx/jsx-runtime";
import { splitDescription } from "../description";
import type { DescriptionSegment } from "../description";

function renderSegment(segment: DescriptionSegment, index: number): JSX.Element | string {
  if (segment.src) return <img key={index} class="description-image" src={segment.src} data-token={segment.src} alt="" />;
  if (segment.href)
    return (
      <a key={index} href={segment.href}>
        {segment.text}
      </a>
    );
  return segment.text;
}

export function DescriptionContent({ description }: { description: string }) {
  return <>{splitDescription(description).map(renderSegment)}</>;
}
