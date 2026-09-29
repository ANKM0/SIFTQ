export type DescriptionSegment = { text: string; href?: string; src?: string };

const DESCRIPTION_PATTERN = /\/api\/images\/[0-9A-Za-z_-]+|https?:\/\/[^\s<>]+/g;
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

  for (const match of description.matchAll(DESCRIPTION_PATTERN)) {
    const matched = match[0];
    const start = match.index ?? cursor;

    if (start > cursor) segments.push({ text: description.slice(cursor, start) });

    if (matched.startsWith("/api/images/")) {
      segments.push({ text: matched, src: matched });
      cursor = start + matched.length;
      continue;
    }

    let end = start + matched.length;
    while (!isDescriptionBoundary(description[end])) end += 1;

    const rawUrl = description.slice(start, end);
    const url = trimDescriptionPunctuation(rawUrl);

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
