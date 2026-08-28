import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vite-plus/test";

const SAMPLE_DOCUMENT = `# Sample Document

Intro paragraph.

## Section A

Content A.

### Subsection A.1

Content A.1.

## Section B

Content B.
`;

type Md2IdxOutput = {
  index: string;
  sections: string[];
};

function isMd2IdxOutput(value: unknown): value is Md2IdxOutput {
  if (typeof value !== "object" || value === null) return false;
  if (!("index" in value) || typeof value.index !== "string") return false;
  if (!("sections" in value) || !Array.isArray(value.sections)) return false;
  return value.sections.every((section) => typeof section === "string");
}

function runMd2Idx(markdown: string): Md2IdxOutput {
  const directory = mkdtempSync(join(tmpdir(), "md2idx-"));
  const fixturePath = join(directory, "sample.md");
  try {
    writeFileSync(fixturePath, markdown, "utf8");
    const bun = process.env["BUN"] ?? "bun";
    const stdout = execFileSync(bun, ["x", "md2idx", fixturePath], {
      cwd: process.cwd(),
      encoding: "utf8",
    });
    const parsed: unknown = JSON.parse(stdout);
    if (!isMd2IdxOutput(parsed)) {
      throw new Error(`md2idx output does not match the { index, sections } contract: ${stdout}`);
    }
    return parsed;
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

describe("md2idx via bun x", () => {
  it("emits a numbered index and per-heading sections in the repository dev environment", () => {
    const output = runMd2Idx(SAMPLE_DOCUMENT);

    expect(output.index).toContain("0. Sample Document");
    expect(output.index).toContain("1. Section A");
    expect(output.index).toContain("2. Subsection A.1");
    expect(output.index).toContain("3. Section B");
    expect(output.sections).toHaveLength(4);
    expect(output.sections[1]).toContain("## Section A");
    expect(output.sections[2]).toContain("### Subsection A.1");
    expect(output.sections[3]).toContain("## Section B");
  });
});
