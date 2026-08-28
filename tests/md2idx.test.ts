import { spawn } from "node:child_process";
import {
  closeSync,
  mkdtempSync,
  openSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
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

function runMd2Idx(markdown: string): Promise<Md2IdxOutput> {
  const directory = mkdtempSync(join(tmpdir(), "md2idx-"));
  const fixturePath = join(directory, "sample.md");
  const stdoutPath = join(directory, "stdout.json");
  const stderrPath = join(directory, "stderr.log");
  const bun = process.env["BUN"] ?? "bun";
  let stdoutFd: number;
  let stderrFd: number;
  try {
    writeFileSync(fixturePath, markdown, "utf8");
    // spawnSync/execFileSync はこの sandbox 環境で EPERM になり、
    // pipe 経由の stdout も欠落するため、非同期 spawn + ファイル fd へ出力する。
    stdoutFd = openSync(stdoutPath, "w");
    stderrFd = openSync(stderrPath, "w");
  } catch (error) {
    rmSync(directory, { recursive: true, force: true });
    return Promise.reject(error);
  }
  return new Promise((resolve, reject) => {
    const child = spawn(bun, ["x", "--no-install", "md2idx", fixturePath], {
      cwd: process.cwd(),
      stdio: ["ignore", stdoutFd, stderrFd],
    });
    let cleaned = false;
    const cleanup = () => {
      if (cleaned) return;
      cleaned = true;
      closeSync(stdoutFd);
      closeSync(stderrFd);
      rmSync(directory, { recursive: true, force: true });
    };
    child.on("error", (error) => {
      cleanup();
      reject(error);
    });
    child.on("exit", (code) => {
      try {
        if (code !== 0) {
          const stderr = readFileSync(stderrPath, "utf8");
          throw new Error(`md2idx exited with code ${code}: ${stderr}`);
        }
        const stdout = readFileSync(stdoutPath, "utf8");
        const parsed: unknown = JSON.parse(stdout);
        if (!isMd2IdxOutput(parsed)) {
          throw new Error(`md2idx output does not match the { index, sections } contract: ${stdout}`);
        }
        resolve(parsed);
      } catch (error) {
        reject(error);
      } finally {
        cleanup();
      }
    });
  });
}

describe("md2idx via bun x", () => {
  it("emits a numbered index and per-heading sections in the repository dev environment", async () => {
    const output = await runMd2Idx(SAMPLE_DOCUMENT);

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
