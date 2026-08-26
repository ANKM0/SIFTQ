import type { FC } from "hono/jsx";

const HTMX_SCRIPT = "https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js";
const SORTABLE_SCRIPT = "https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js";
export const MATRIX_DND_SCRIPT = [
  "function showDndConflict() {",
  '  var notice = document.getElementById("dnd-conflict");',
  "  if (notice) notice.hidden = false;",
  "}",
  "function restoreMatrix() {",
  '  fetch("/", { headers: { "HX-Request": "true" } })',
  "    .then(function (response) { return response.text(); })",
  "    .then(function (html) {",
  '      var page = document.getElementById("page");',
  "      if (page) page.innerHTML = html;",
  "      showDndConflict();",
  "      initMatrixSortable();",
  "    });",
  "}",
  "function initMatrixSortable() {",
  '  var lists = document.querySelectorAll(".matrix-cards[data-sortable-group]");',
  '  if (typeof Sortable === "undefined") return;',
  "  lists.forEach(function (list) {",
  "    if (Sortable.get(list)) return;",
  '    Sortable.create(list, { group: "matrix", animation: 150, onEnd: function (evt) {',
  "      var card = evt.item;",
  "      var target = evt.to;",
  '      var taskId = card.getAttribute("data-task-id");',
  '      var version = card.getAttribute("data-version");',
  '      var area = target.getAttribute("data-area");',
  "      if (!taskId || !version || area === null) return;",
  '      fetch("/api/tasks/reorder", {',
  '        method: "POST",',
  '        headers: { "Content-Type": "application/json" },',
  "        body: JSON.stringify({ id: taskId, area: Number(area), order: evt.newIndex, version: Number(version) }),",
  "      }).then(function (response) {",
  "        if (!response.ok) { showDndConflict(); restoreMatrix(); return null; }",
  "        return response.json();",
  "      }).then(function (task) {",
  "        if (!task) return;",
  '        card.setAttribute("data-version", String(task.version));',
  "      });",
  "    }});",
  "  });",
  "}",
  'document.addEventListener("DOMContentLoaded", initMatrixSortable);',
  'document.addEventListener("htmx:load", initMatrixSortable);',
].join("\n");

export const Layout: FC = ({ children }) => (
  <html lang="ja">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>SIFTQ</title>
      <link rel="stylesheet" href="/styles.css" />
      <script src={HTMX_SCRIPT} defer></script>
      <script src={SORTABLE_SCRIPT} defer></script>
      <script src="/matrix-dnd.js" defer></script>
    </head>
    <body>
      <main id="page">{children}</main>
    </body>
  </html>
);
