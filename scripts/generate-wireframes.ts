import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { createSession, SESSION_COOKIE_NAME } from "../src/auth";
import app from "../src/index";
import { MemoryTaskRepository } from "../src/preview/MemoryTaskRepository";
import { PREVIEW_TASKS } from "../src/preview/tasks";
import type { Task } from "../src/task";
import type { TaskRepository } from "../src/task-repository";

const OUTPUT_DIRECTORY = resolve("docs/wireframes");
const PREVIEW_TASK_ID = "preview-task";
const PREVIEW_PASSWORD = PREVIEW_TASK_ID;
const PREVIEW_SECRET = "preview-secret";
const PREVIEW_TOOLBAR =
  '<div class="preview-toolbar"><span>Static mock preview</span><a class="button" href="./index.html" title="固定モックデータの UI プレビュー一覧へ戻る">UI Preview</a></div>';

const PREVIEW_STYLES = `
.preview-toolbar {
  align-items: center;
  background: #fff8c5;
  border-bottom: 1px solid #d4a72c;
  color: #4d2d00;
  display: flex;
  font-size: 13px;
  font-weight: 700;
  gap: 12px;
  justify-content: flex-end;
  padding: 8px 20px;
}

/* Wireframe-only editor layout. The production layout remains unchanged. */
.page--editor {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 121px);
  min-height: 480px;
  overflow: auto;
}

.page--editor .detail-grid {
  flex: 1;
  min-height: 0;
}

.page--editor .form-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.page--editor .form-panel > label:has(textarea) {
  flex: 1;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 180px;
}

.page--editor textarea {
  flex: 1;
  height: 100%;
  min-height: 180px;
}

.wireframe-editor .preview-meta-trigger {
  background: transparent;
  border: 0;
  color: inherit;
  cursor: pointer;
  font: inherit;
  text-align: inherit;
  width: 100%;
}

.wireframe-editor .preview-meta-value {
  cursor: pointer;
}

.wireframe-editor .preview-popover[hidden] {
  display: none;
}

.wireframe-editor .preview-popover .status-choice {
  background: #ffffff;
  border: 0;
  color: inherit;
  cursor: pointer;
  font: inherit;
  text-align: left;
  width: 100%;
}

.wireframe-editor .preview-popover .status-choice.selected {
  background: #f6f8fa;
}

/* Wireframe-only Matrix cards inspired by a project board layout. */
.page--matrix .matrix-cards {
  display: grid;
  gap: 12px;
}

.page--matrix .matrix-task-card {
  background: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 10px;
  box-shadow: 0 1px 2px rgb(31 35 40 / 12%);
  display: flex;
  flex-direction: column;
  margin: 0;
  min-height: 104px;
  padding: 12px;
}

.page--matrix .matrix-task-card:hover {
  border-color: #0969da;
  box-shadow: 0 0 0 2px #ddf4ff;
}

.matrix-task-card .task-card-header {
  align-items: flex-start;
  display: flex;
  gap: 8px;
  justify-content: space-between;
}

.matrix-task-card .task-title {
  font-size: 14px;
  line-height: 1.45;
}

.matrix-task-card .status {
  font-size: 12px;
}
`;

export const PREVIEW_PAGE_PATHS = [
  ["matrix-page.html", "/"],
  ["task-list.html", "/tasks"],
  ["task-detail.html", `/tasks/${PREVIEW_TASK_ID}`],
  ["task-create-result.html", `/tasks/${PREVIEW_TASK_ID}`],
  ["task-new.html", "/tasks/new"],
  ["task-new-area-1.html", "/tasks/new?area=1"],
  ["task-new-area-2.html", "/tasks/new?area=2"],
  ["task-new-area-3.html", "/tasks/new?area=3"],
  ["task-new-area-4.html", "/tasks/new?area=4"],
  ["task-new-status-selected.html", "/tasks/new?status=done"],
  ["task-new-area-selected.html", "/tasks/new?area=3"],
] as const;

type EditorMode = "new" | "detail";
type EditorMenu = "status" | "area";
type EditorStatus = "do" | "done" | "skip";
type EditorArea = 1 | 2 | 3 | 4;

export type EditorWireframeOptions = {
  mode: EditorMode;
  status: EditorStatus;
  area: EditorArea;
  cancelHref?: string;
  openMenu?: EditorMenu;
  taskTitle?: string;
  description?: string;
};

const STATUS_DESCRIPTIONS: Record<EditorStatus, string> = {
  do: "Visible on the matrix.",
  done: "Completed. Area is preserved.",
  skip: "Skipped. Area is preserved.",
};

const STATUS_DOT_CLASSES: Record<EditorStatus, string> = {
  do: "status-dot status-dot--do",
  done: "status-dot status-dot--done",
  skip: "status-dot status-dot--skip",
};

const AREA_DOT_CLASSES: Record<EditorArea, string> = {
  1: "status-dot status-dot--one",
  2: "status-dot status-dot--two",
  3: "status-dot status-dot--three",
  4: "status-dot status-dot--four",
};

function renderChoice(menu: EditorMenu, value: EditorStatus | EditorArea, selected: boolean): string {
  const marker = selected ? '<span class="check">✓</span>' : '<span class="box"></span>';
  if (menu === "status") {
    if (typeof value !== "string") throw new Error(`Unknown status value: ${value}`);
    return `<button class="status-choice${selected ? " selected" : ""}" type="button" data-meta-choice="${menu}" data-value="${value}">${marker}<span class="${STATUS_DOT_CLASSES[value]}"></span><span><strong>${value}</strong><br /><span class="muted">${STATUS_DESCRIPTIONS[value]}</span></span></button>`;
  }
  if (typeof value !== "number") throw new Error(`Unknown area value: ${value}`);
  return `<button class="status-choice${selected ? " selected" : ""}" type="button" data-meta-choice="${menu}" data-value="${value}">${marker}<span class="${AREA_DOT_CLASSES[value]}"></span><span><strong>${value}</strong><br /><span class="muted">Matrix quadrant.</span></span></button>`;
}

function renderPopover(menu: EditorMenu, selected: EditorStatus | EditorArea, open: boolean): string {
  const title = menu === "status" ? "Apply status to this task" : "Apply area to this task";
  const selectedTitle = menu === "status" ? "Selected status" : "Selected area";
  const values = menu === "status" ? (["do", "done", "skip"] as const) : ([1, 2, 3, 4] as const);
  const selectedChoice = values.find((value) => value === selected);
  const suggestions = values.filter((value) => value !== selected);
  if (selectedChoice === undefined) throw new Error(`Unknown ${menu} value: ${selected}`);

  return `<section id="${menu}-popover" class="popover preview-popover" aria-label="${title}"${open ? "" : " hidden"}><h3>${title}</h3><div class="status-group-title">${selectedTitle}</div>${renderChoice(menu, selectedChoice, true)}<div class="status-group-title">Suggestions</div>${suggestions.map((value) => renderChoice(menu, value, false)).join("")}<button class="status-choice preview-dialog-cancel" type="button">Cancel</button></section>`;
}

function renderMetadata(options: EditorWireframeOptions): string {
  const statusOpen = options.openMenu === "status";
  const areaOpen = options.openMenu === "area";
  return `<aside id="task-meta" class="side-panel side-panel--popover-open"><button class="meta-row meta-row-link preview-meta-trigger" type="button" data-meta-trigger="status" aria-expanded="${statusOpen}" aria-controls="status-popover"><h2>Status</h2><span class="meta-caret" aria-hidden="true">▾</span></button><button class="status status--${options.status} preview-meta-value" type="button" data-meta-trigger="status" data-meta-value="status">${options.status}</button><button class="meta-row meta-row-link meta-row--spaced preview-meta-trigger" type="button" data-meta-trigger="area" aria-expanded="${areaOpen}" aria-controls="area-popover"><h2>Area</h2><span class="meta-caret" aria-hidden="true">▾</span></button><button class="status area-badge preview-meta-value" type="button" data-meta-trigger="area" data-meta-value="area">${options.area}</button>${renderPopover("status", options.status, statusOpen)}${renderPopover("area", options.area, areaOpen)}</aside>`;
}

const EDITOR_SCRIPT = `<script>
(() => {
  const panel = document.getElementById("task-meta");
  if (!(panel instanceof HTMLElement)) return;
  const closePopovers = () => {
    panel.querySelectorAll(".preview-popover").forEach((popover) => { popover.hidden = true; });
    panel.querySelectorAll("[data-meta-trigger]").forEach((trigger) => { trigger.setAttribute("aria-expanded", "false"); });
  };
  panel.querySelectorAll("[data-meta-trigger]").forEach((trigger) => {
    trigger.addEventListener("click", () => {
      const menu = trigger.getAttribute("data-meta-trigger");
      const popover = document.getElementById(menu + "-popover");
      if (!(popover instanceof HTMLElement)) return;
      const willOpen = popover.hidden;
      closePopovers();
      popover.hidden = !willOpen;
      panel.querySelectorAll('[data-meta-trigger="' + menu + '"]').forEach((menuTrigger) => { menuTrigger.setAttribute("aria-expanded", String(willOpen)); });
    });
  });
  panel.querySelectorAll("[data-meta-choice]").forEach((choice) => {
    choice.addEventListener("click", () => {
      const menu = choice.getAttribute("data-meta-choice");
      const value = choice.getAttribute("data-value");
      if ((menu !== "status" && menu !== "area") || value === null) return;
      panel.querySelectorAll('[data-meta-choice="' + menu + '"]').forEach((option) => {
        const selected = option === choice;
        option.classList.toggle("selected", selected);
        const mark = option.querySelector(".check, .box");
        if (mark === null) return;
        mark.className = selected ? "check" : "box";
        mark.textContent = selected ? "✓" : "";
      });
      panel.querySelectorAll('[data-meta-value="' + menu + '"]').forEach((badge) => {
        badge.textContent = value;
        badge.className = menu === "status" ? "status status--" + value + " preview-meta-value" : "status area-badge preview-meta-value";
      });
      closePopovers();
    });
  });
  panel.querySelectorAll(".preview-dialog-cancel").forEach((cancel) => { cancel.addEventListener("click", closePopovers); });
  document.addEventListener("click", (event) => { if (event.target instanceof Node && !panel.contains(event.target)) closePopovers(); });
})();
</script>`;

export function renderEditorWireframe(options: EditorWireframeOptions): string {
  const isNew = options.mode === "new";
  const title = isNew ? "New task" : "Task detail";
  const topAction = isNew ? "" : '<a class="button" href="./task-list.html">Tasks</a>';
  const cancelHref = options.cancelHref ?? "./task-list.html";
  const taskTitle = options.taskTitle ?? "Matrix のタスクカードを見直す";
  const titleValue = isNew ? "" : ` value="${taskTitle}"`;
  const description = isNew ? "" : (options.description ?? "タスクの内容を確認しやすいカード表現を検討する。");
  const version = isNew ? "" : '<input type="hidden" name="version" value="1" />';
  const primaryAction = isNew ? "Create" : "Save";
  return `<!doctype html><html lang="ja"><head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><title>SIFTQ — ${title}</title><link rel="stylesheet" href="./styles.css" /></head><body>${PREVIEW_TOOLBAR}<header class="topbar"><a class="brand" href="./matrix-page.html">SIFTQ</a><nav class="nav" aria-label="Primary"><a href="./matrix-page.html">Matrix</a><a class="active" href="./task-list.html">Tasks</a></nav></header><main id="page"><div class="page page--editor page--${options.mode} wireframe-editor" data-state="normal"><div class="page-header"><h1 class="page-title">${title}</h1>${topAction}</div><div class="detail-grid"><form class="form-panel"><label>Title<input type="text" name="title"${titleValue} maxlength="256" required /></label>${version}<label>Description<textarea name="description">${description}</textarea></label><div class="form-actions"><a class="button" href="${cancelHref}">Cancel</a><button class="button primary" type="submit">${primaryAction}</button></div></form>${renderMetadata(options)}</div></div></main>${EDITOR_SCRIPT}</body></html>`;
}

function detailOptions(task: Task, openMenu?: EditorMenu, cancelHref?: string): EditorWireframeOptions {
  const base = {
    mode: "detail",
    status: task.status,
    area: task.area,
    taskTitle: task.title,
    description: task.description,
  } as const;
  return {
    ...base,
    ...(openMenu === undefined ? {} : { openMenu }),
    ...(cancelHref === undefined ? {} : { cancelHref }),
  };
}

const TASK_DETAIL_WIREFRAMES: ReadonlyArray<readonly [string, EditorWireframeOptions]> = PREVIEW_TASKS.map(
  (task, index) => [`task-detail-${index + 1}.html`, detailOptions(task)],
);

const MATRIX_TASK_DETAIL_WIREFRAMES: ReadonlyArray<readonly [string, EditorWireframeOptions]> = PREVIEW_TASKS.flatMap(
  (task, index) => task.status === "do"
    ? [[`task-detail-${index + 1}-matrix.html`, detailOptions(task, undefined, "./matrix-page.html")] as const]
    : [],
);

const PRIMARY_PREVIEW_TASK = PREVIEW_TASKS[0];
if (PRIMARY_PREVIEW_TASK === undefined) throw new Error("Preview task is missing");

const EDITOR_WIREFRAMES: ReadonlyArray<readonly [string, EditorWireframeOptions]> = [
  ["task-detail.html", detailOptions(PRIMARY_PREVIEW_TASK)],
  ["task-create-result.html", detailOptions(PRIMARY_PREVIEW_TASK)],
  ["task-status-menu.html", detailOptions(PRIMARY_PREVIEW_TASK, "status")],
  ["task-area-menu.html", detailOptions(PRIMARY_PREVIEW_TASK, "area")],
  ["task-new.html", { mode: "new", status: "do", area: 2 }],
  ["task-new-area-1.html", { mode: "new", status: "do", area: 1 }],
  ["task-new-area-2.html", { mode: "new", status: "do", area: 2 }],
  ["task-new-area-3.html", { mode: "new", status: "do", area: 3 }],
  ["task-new-area-4.html", { mode: "new", status: "do", area: 4 }],
  ["task-new-status-menu.html", { mode: "new", status: "do", area: 2, openMenu: "status" }],
  ["task-new-area-menu.html", { mode: "new", status: "do", area: 2, openMenu: "area" }],
  ["task-new-status-selected.html", { mode: "new", status: "done", area: 2 }],
  ["task-new-area-selected.html", { mode: "new", status: "do", area: 3 }],
  ...TASK_DETAIL_WIREFRAMES,
  ...MATRIX_TASK_DETAIL_WIREFRAMES,
];

const TASK_DETAIL_FILES: ReadonlyMap<string, string> = new Map(
  PREVIEW_TASKS.map((task, index) => [`/tasks/${task.id}`, `./task-detail-${index + 1}.html`] as const),
);

const MATRIX_TASK_DETAIL_LINKS: ReadonlyMap<string, string> = new Map(
  PREVIEW_TASKS.flatMap((task, index) => task.status === "do"
    ? [[`./task-detail-${index + 1}.html`, `./task-detail-${index + 1}-matrix.html`] as const]
    : []),
);

const PREVIEW_LINKS: ReadonlyMap<string, string> = new Map([
  ...TASK_DETAIL_FILES,
  [`/tasks/${PREVIEW_TASK_ID}/status/menu`, "./task-status-menu.html"],
  [`/tasks/${PREVIEW_TASK_ID}/area/menu`, "./task-area-menu.html"],
  ["/tasks/new", "./task-new.html"],
  ["/tasks", "./task-list.html"],
  ["/", "./matrix-page.html"],
]);

function previewBindings(repository: TaskRepository) {
  return {
    TASK_REPOSITORY: repository,
    AUTH_PASSWORD: PREVIEW_PASSWORD,
    SESSION_SECRET: PREVIEW_SECRET,
  };
}

async function previewRequest(path: string, repository: TaskRepository): Promise<Response> {
  const session = await createSession(PREVIEW_SECRET, Date.now() + 60_000);
  return app.request(
    path,
    { headers: { Cookie: `${SESSION_COOKIE_NAME}=${session}` } },
    previewBindings(repository),
  );
}

function rewriteLink(href: string): string {
  const previewLink = PREVIEW_LINKS.get(href);
  if (previewLink !== undefined) return previewLink;
  const selectedArea = href.match(/^\/tasks\/new\?area=([1-4])$/)?.[1];
  if (selectedArea !== undefined) return `./task-new-area-${selectedArea}.html`;
  if (href.startsWith("/tasks/new")) return "./task-new.html";
  if (href.startsWith("/tasks/")) return "./task-detail.html";
  return href;
}

export function staticPreviewHtml(html: string): string {
  return html
    .replace('href="/styles.css"', 'href="./styles.css"')
    .replace(/<script\b[^>]*><\/script>/g, "")
    .replace(/ hx-[\w-]+=("[^"]*"|'[^']*')/g, "")
    .replace(/href="([^"]+)"/g, (_match, href: string) => `href="${rewriteLink(href)}"`)
    .replace("<body>", `<body>${PREVIEW_TOOLBAR}`);
}

export function staticMatrixPreviewHtml(html: string): string {
  const preview = staticPreviewHtml(html).replace(/href="([^"]+)"/g, (match, href: string) => {
    const matrixDetailLink = MATRIX_TASK_DETAIL_LINKS.get(href);
    return matrixDetailLink === undefined ? match : `href="${matrixDetailLink}"`;
  });
  return preview.replace(
    /<a class="task-card"([^>]*)href="([^"]+)"([^>]*)><span class="task-title">([\s\S]*?)<\/span><\/a>/g,
    (match, beforeHref: string, href: string, afterHref: string, title: string) => {
      const taskIndex = PREVIEW_TASKS.findIndex(
        (task, index) => task.status === "do" && href === `./task-detail-${index + 1}-matrix.html`,
      );
      const task = PREVIEW_TASKS[taskIndex];
      if (task === undefined) return match;
      return `<a class="task-card matrix-task-card"${beforeHref}href="${href}"${afterHref}><span class="task-card-header"><span class="task-title">${title}</span><span class="status status--${task.status}">${task.status}</span></span></a>`;
    },
  );
}

export function replaceTaskMeta(page: string, menu: string): string {
  return page.replace(/<aside id="task-meta"[\s\S]*?<\/aside>/, menu);
}

export function openNewTaskMenu(page: string, menu: "status" | "area"): string {
  return page.replace(
    `<details class="side-panel--popover-open" data-menu="${menu}">`,
    `<details class="side-panel--popover-open" data-menu="${menu}" open>`,
  );
}

async function writeOutput(path: string, content: string): Promise<void> {
  const outputPath = resolve(OUTPUT_DIRECTORY, path);
  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, content, "utf8");
}

async function renderPreview(path: string, repository: TaskRepository): Promise<string> {
  const response = await previewRequest(path, repository);
  if (!response.ok) throw new Error(`Could not render ${path}: ${response.status}`);
  return response.text();
}

async function main(): Promise<void> {
  const repository = new MemoryTaskRepository(PREVIEW_TASKS);

  const css = await renderPreview("/styles.css", repository);
  await writeOutput("styles.css", `${css}\n${PREVIEW_STYLES}`);

  const pages = await Promise.all(
    PREVIEW_PAGE_PATHS.map(async ([fileName, path]) => [fileName, await renderPreview(path, repository)] as const),
  );
  for (const [fileName, page] of pages) {
    const staticPage = fileName === "matrix-page.html" ? staticMatrixPreviewHtml(page) : staticPreviewHtml(page);
    await writeOutput(fileName, `<!-- Generated by scripts/generate-wireframes.ts. Do not edit. -->\n${staticPage}`);
  }

  for (const [fileName, options] of EDITOR_WIREFRAMES) {
    await writeOutput(fileName, `<!-- Generated by scripts/generate-wireframes.ts. Do not edit. -->\n${renderEditorWireframe(options)}`);
  }

  await writeOutput(
    "index.html",
    `<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SIFTQ UI Preview</title>
    <link rel="stylesheet" href="./styles.css" />
  </head>
  <body>
    <main class="page">
      <div class="page-header">
        <div>
          <h1 class="page-title">SIFTQ UI Preview</h1>
          <p class="muted">実コンポーネントを固定モックデータで描画した静的プレビュー。</p>
        </div>
      </div>
      <div class="list" aria-label="Preview states">
        <a class="task-row" href="./matrix-page.html"><span class="issue-number">P01</span><strong>Matrix</strong></a>
        <a class="task-row" href="./task-list.html"><span class="issue-number">P02</span><strong>Task list</strong></a>
        <a class="task-row" href="./task-detail.html"><span class="issue-number">P03</span><strong>Task detail</strong></a>
        <a class="task-row" href="./task-new.html"><span class="issue-number">P04</span><strong>New task (default area 2)</strong></a>
        <a class="task-row" href="./task-new-area-1.html"><span class="issue-number">P04a</span><strong>New task (Matrix area 1)</strong></a>
        <a class="task-row" href="./task-new-area-2.html"><span class="issue-number">P04b</span><strong>New task (Matrix area 2)</strong></a>
        <a class="task-row" href="./task-new-area-3.html"><span class="issue-number">P04c</span><strong>New task (Matrix area 3)</strong></a>
        <a class="task-row" href="./task-new-area-4.html"><span class="issue-number">P04d</span><strong>New task (Matrix area 4)</strong></a>
        <a class="task-row" href="./task-create-result.html"><span class="issue-number">P04e</span><strong>Create result (task detail)</strong></a>
        <a class="task-row" href="./task-status-menu.html"><span class="issue-number">P05</span><strong>Status menu</strong></a>
        <a class="task-row" href="./task-area-menu.html"><span class="issue-number">P06</span><strong>Area menu</strong></a>
        <a class="task-row" href="./task-new-status-menu.html"><span class="issue-number">P07</span><strong>New task status menu</strong></a>
        <a class="task-row" href="./task-new-area-menu.html"><span class="issue-number">P08</span><strong>New task area menu</strong></a>
        <a class="task-row" href="./task-new-status-selected.html"><span class="issue-number">P09</span><strong>New task selected status</strong></a>
        <a class="task-row" href="./task-new-area-selected.html"><span class="issue-number">P10</span><strong>New task selected area</strong></a>
      </div>
    </main>
  </body>
</html>
`,
  );
}

if (process.argv[1]?.endsWith("generate-wireframes.ts")) {
  void main().catch((error: unknown) => {
    console.error(error);
    process.exitCode = 1;
  });
}
