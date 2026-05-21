import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";

import { afterEach, describe, expect, it } from "vitest";

const fixtureDirectory = ".takt/markdown-ci-contract";
const fixturePath = `${fixtureDirectory}/bad.md`;

describe("Markdown CI contract", () => {
  afterEach(() => {
    rmSync(fixtureDirectory, { recursive: true, force: true });
  });

  it("excludes generated TAKT run artifacts from Markdown checks", () => {
    mkdirSync(fixtureDirectory, { recursive: true });
    writeFileSync(fixturePath, "# Generated\n\ntrailing whitespace  ", "utf8");

    expect(() =>
      execFileSync("uv", ["run", "python", "scripts/ci/check_markdown.py"], {
        env: {
          ...process.env,
          UV_CACHE_DIR: "/tmp/siftq-markdown-ci-contract-uv-cache"
        },
        stdio: "pipe"
      })
    ).not.toThrow();
  });
});
