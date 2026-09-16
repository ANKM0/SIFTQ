import { existsSync } from "node:fs";
import { patchSvgDimensions } from "./generate";

const outDir = new URL("../../docs/requirements/assets/domain-model/generated/", import.meta.url);
const names = ["domain-model", "logical", "physical", "flow", "nav"];

for (const name of names) {
  const file = new URL(`${name}.svg`, outDir);
  if (existsSync(file)) patchSvgDimensions(file);
}
