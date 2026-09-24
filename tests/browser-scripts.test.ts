import { describe, expect, it } from "vite-plus/test";
import {
  createSourceFile,
  forEachChild,
  isVariableDeclarationList,
  NodeFlags,
  ScriptKind,
  ScriptTarget,
  transpileModule,
} from "typescript";
import type { Node } from "typescript";
import {
  HTMX_CONFLICT_SWAP_SCRIPT,
  POPOVER_DISMISS_SCRIPT,
  TASK_FORM_SHORTCUT_SCRIPT,
} from "../src/client/browser-scripts";
import { MATRIX_DND_SCRIPT } from "../src/client/matrix-scripts";
import { DESCRIPTION_EDITOR_SCRIPT } from "../src/client/task-form-scripts";
import { TASK_LIST_SELECTION_SCRIPT } from "../src/client/task-list-scripts";

const scripts = [
  ["HTMX conflict swap", HTMX_CONFLICT_SWAP_SCRIPT],
  ["popover dismissal", POPOVER_DISMISS_SCRIPT],
  ["task form shortcut", TASK_FORM_SHORTCUT_SCRIPT],
  ["description editor", DESCRIPTION_EDITOR_SCRIPT],
  ["task list selection", TASK_LIST_SELECTION_SCRIPT],
  ["Matrix drag and drop", MATRIX_DND_SCRIPT],
] as const;

describe("browser scripts", () => {
  it.each(scripts)("%s is valid JavaScript using block-scoped declarations", (_name, script) => {
    const source = createSourceFile("browser-script.js", script, ScriptTarget.Latest, true, ScriptKind.JS);
    const transpiled = transpileModule(script, {
      compilerOptions: { allowJs: true, target: ScriptTarget.Latest },
      reportDiagnostics: true,
    });
    let usesVar = false;

    function visit(node: Node): void {
      if (isVariableDeclarationList(node) && node.flags === NodeFlags.None) usesVar = true;
      forEachChild(node, visit);
    }

    visit(source);

    expect(transpiled.diagnostics).toEqual([]);
    expect(usesVar).toBe(false);
  });
});
