import { describe, expect, it } from "vitest";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import pkg from "../package.json";

const ROOT_DIR = fileURLToPath(new URL("..", import.meta.url));

const FORBIDDEN_DIRECT_DEPENDENCIES: readonly string[] = [
  "react",
  "react-dom",
  "@dnd-kit/core",
  "@dnd-kit/sortable",
  "@dnd-kit/utilities",
  "@vitejs/plugin-react",
  "@types/react",
  "@types/react-dom",
  "@testing-library/react",
  "eslint-plugin-react-hooks",
  "eslint-plugin-react-refresh",
  "jsdom",
  "vite",
];

const FORBIDDEN_IMPORT_SPECIFIERS: readonly string[] = [
  "react",
  "react-dom",
  "react-dom/client",
  "@vitejs/plugin-react",
];

const FORBIDDEN_IMPORT_PREFIXES: readonly string[] = ["@dnd-kit/"];

const SCAN_DIRECTORIES: readonly string[] = ["src", "tests"];
const SCAN_FILES: readonly string[] = ["vite.config.ts"];

function isForbiddenImport(specifier: string): boolean {
  return (
    FORBIDDEN_IMPORT_SPECIFIERS.includes(specifier) ||
    FORBIDDEN_IMPORT_PREFIXES.some((prefix) => specifier.startsWith(prefix))
  );
}

function moduleSpecifiers(source: string): string[] {
  const patterns = [
    /\bfrom\s*(["'])([^"']+)\1/g,
    /\bimport\s*(["'])([^"']+)\1/g,
    /\bimport\s*\(\s*(["'])([^"']+)\1\s*\)/g,
  ];
  const specifiers: string[] = [];
  for (const pattern of patterns) {
    for (const match of source.matchAll(pattern)) {
      const specifier = match[2];
      if (specifier !== undefined) specifiers.push(specifier);
    }
  }
  return specifiers;
}

function tsFilesUnder(directory: string): string[] {
  const entries = readdirSync(join(ROOT_DIR, directory), { recursive: true });
  const files: string[] = [];
  for (const entry of entries) {
    const relativePath = String(entry);
    if (!relativePath.endsWith(".ts") && !relativePath.endsWith(".tsx")) {
      continue;
    }
    files.push(join(ROOT_DIR, directory, relativePath));
  }
  return files;
}

describe("React / dnd-kit removal contract", () => {
  it("keeps hono as the only production dependency", () => {
    const dependencies = Object.keys(pkg.dependencies ?? {});
    expect(dependencies).toEqual(["hono"]);
  });

  it("does not declare React, dnd-kit, or React Vite plugin packages as direct dependencies", () => {
    const directDependencies = [
      ...Object.keys(pkg.dependencies ?? {}),
      ...Object.keys(pkg.devDependencies ?? {}),
    ];
    const forbidden = directDependencies.filter((name) =>
      FORBIDDEN_DIRECT_DEPENDENCIES.includes(name),
    );
    expect(forbidden).toEqual([]);
  });

  it("does not import React, React DOM, dnd-kit, or the React Vite plugin in src, tests, or vite.config.ts", () => {
    const files = [
      ...SCAN_DIRECTORIES.flatMap((directory) => tsFilesUnder(directory)),
      ...SCAN_FILES.map((file) => join(ROOT_DIR, file)),
    ];
    const violations: string[] = [];
    for (const file of files) {
      const source = readFileSync(file, "utf8");
      const forbidden = moduleSpecifiers(source).filter(isForbiddenImport);
      if (forbidden.length > 0) {
        violations.push(`${file}: ${forbidden.join(", ")}`);
      }
    }
    expect(violations).toEqual([]);
  });

  it("does not recreate the legacy React entry paths", () => {
    expect(existsSync(join(ROOT_DIR, "src", "main.tsx"))).toBe(false);
    expect(existsSync(join(ROOT_DIR, "index.html"))).toBe(false);
  });
});
