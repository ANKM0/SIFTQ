import { renderToString } from "hono/jsx/dom/server";
import { describe, expect, it } from "vite-plus/test";
import { IdeaDetailFields } from "../src/views/IdeaDetailFields";

describe("IdeaDetailFields", () => {
  it("renders a linkified description URL and a plain text hidden value", () => {
    const html = renderToString(
      <IdeaDetailFields title="メモ" description="Read https://example.com/docs now" />,
    );
    expect(html).toContain('data-description-editor="true"');
    expect(html).toContain('<a href="https://example.com/docs">https://example.com/docs</a>');
    expect(html).toContain('name="description"');
    expect(html).toContain('data-description-value="true"');
    expect(html).toContain(">Read https://example.com/docs now</textarea>");
  });

  it("does not linkify non-http URLs", () => {
    const html = renderToString(
      <IdeaDetailFields title="メモ" description="javascript:alert(1) www.example.com" />,
    );
    expect(html).not.toContain("<a ");
  });

  it("adds the empty modifier only when the description is blank", () => {
    const emptyHtml = renderToString(<IdeaDetailFields title="メモ" description="" />);
    expect(emptyHtml).toContain("idea-detail__description--empty");

    const filledHtml = renderToString(<IdeaDetailFields title="メモ" description="本文" />);
    expect(filledHtml).not.toContain("idea-detail__description--empty");
  });
});
