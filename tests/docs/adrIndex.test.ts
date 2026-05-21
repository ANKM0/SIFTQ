import { describe, expect, it } from "vitest";

const adrDocuments = import.meta.glob<string>("../../docs/adr/*.md", {
  eager: true,
  import: "default",
  query: "?raw"
});

describe("ADR index", () => {
  it("lists every numbered ADR document", () => {
    const givenAdrIndex = adrDocuments["../../docs/adr/README.md"];
    const givenAdrFiles = Object.keys(adrDocuments)
      .map((documentPath) => documentPath.replace("../../docs/adr/", ""))
      .filter((fileName) => /^\d{4}-.+\.md$/.test(fileName))
      .sort();

    const whenListedAdrFiles = givenAdrFiles.filter((fileName) =>
      givenAdrIndex.includes(`](./${fileName})`)
    );

    expect(whenListedAdrFiles).toEqual(givenAdrFiles);
  });
});
