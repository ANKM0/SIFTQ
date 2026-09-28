import { readFileSync, writeFileSync } from "node:fs";

export function patchSvgDimensions(file: string): void {
  const svg = readFileSync(file, "utf8");
  const tag = /<svg\b([^>]*)>/.exec(svg);
  if (tag === null) return;
  const match = tag[0];
  const attrs = tag[1];
  if (match === undefined || attrs === undefined || attrs.includes("width=")) return;
  const viewBox = /viewBox="[-\d.]+ [-\d.]+ ([-\d.]+) ([-\d.]+)"/.exec(attrs);
  const width = viewBox?.[1];
  const height = viewBox?.[2];
  if (width === undefined || height === undefined) return;
  writeFileSync(file, svg.replace(match, `<svg${attrs} width="${width}" height="${height}">`));
}
