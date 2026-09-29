import { renderToString } from "hono/jsx/dom/server";
import { describe, expect, it } from "vite-plus/test";
import { DescriptionContent } from "../src/components/DescriptionContent";

describe("DescriptionContent", () => {
  it("renders text as-is", () => {
    const html = renderToString(<DescriptionContent description="plain text" />);

    expect(html).toContain("plain text");
    expect(html).not.toContain("<img");
  });

  it("renders an image token as an image", () => {
    const html = renderToString(<DescriptionContent description={"before /api/images/abc-123 after"} />);

    expect(html).toContain('class="description-image"');
    expect(html).toContain('src="/api/images/abc-123"');
    expect(html).toContain("before ");
    expect(html).toContain(" after");
  });

  it("renders an http URL as a link", () => {
    const html = renderToString(<DescriptionContent description="see https://example.com/docs" />);

    expect(html).toContain('href="https://example.com/docs"');
  });
});
