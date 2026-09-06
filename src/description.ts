export type DescriptionSegment = { text: string; href?: string };

const DESCRIPTION_URL_START_PATTERN = /https?:\/\//g;
const DESCRIPTION_TRAILING_PUNCTUATION = ".,!?;:";

function isDescriptionBoundary(character: string | undefined): boolean {
  return character === undefined || /[\s<>]/.test(character);
}

function trimDescriptionPunctuation(url: string): string {
  let end = url.length;
  while (end > 0 && DESCRIPTION_TRAILING_PUNCTUATION.includes(url.charAt(end - 1))) end -= 1;
  return url.slice(0, end);
}

export function splitDescription(description: string): DescriptionSegment[] {
  const segments: DescriptionSegment[] = [];
  let cursor = 0;

  for (const match of description.matchAll(DESCRIPTION_URL_START_PATTERN)) {
    const start = match.index ?? cursor;
    let end = start + match[0].length;
    while (!isDescriptionBoundary(description[end])) end += 1;

    const rawUrl = description.slice(start, end);
    const url = trimDescriptionPunctuation(rawUrl);

    if (start > cursor) segments.push({ text: description.slice(cursor, start) });
    if (url === "") {
      segments.push({ text: rawUrl });
    } else {
      segments.push({ text: url, href: url });
      if (url.length < rawUrl.length) segments.push({ text: rawUrl.slice(url.length) });
    }
    cursor = start + rawUrl.length;
  }

  if (cursor < description.length) segments.push({ text: description.slice(cursor) });
  return segments;
}
