import type { FC } from "hono/jsx";
import type { JSX } from "hono/jsx/jsx-runtime";

const HTMX_SCRIPT = "https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js";
const HTMX_CONFLICT_SWAP_SCRIPT = [
  "document.body.addEventListener('htmx:beforeSwap', function (event) {",
  "  if (event.detail.xhr.status !== 409) return;",
  "  event.detail.shouldSwap = true;",
  "  event.detail.isError = false;",
  "});",
].join("\n");
const POPOVER_DISMISS_SCRIPT = [
  "document.addEventListener('click', function (event) {",
  "  var panel = document.querySelector('[data-popover-close-href]');",
  "  if (!panel || panel.contains(event.target)) return;",
  "  var href = panel.getAttribute('data-popover-close-href');",
  "  if (href) window.location.assign(href);",
  "});",
].join("\n");
export const MATRIX_DND_SCRIPT = [
  "var matrixDraggingCard = null;",
  "var matrixDropTarget = null;",
  "var matrixDndPending = false;",
  "var suppressMatrixCardClick = false;",
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
  "      initMatrixDnd();",
  "    });",
  "}",
  "function matrixCards(list) {",
  '  return Array.prototype.slice.call(list.querySelectorAll(":scope > .task-card"));',
  "}",
  "function matrixDropIndex(list, pointerY) {",
  "  var cards = matrixCards(list).filter(function (card) { return card !== matrixDraggingCard; });",
  "  for (var index = 0; index < cards.length; index += 1) {",
  "    var box = cards[index].getBoundingClientRect();",
  "    if (pointerY < box.top + box.height / 2) return index;",
  "  }",
  "  return cards.length;",
  "}",
  "function setMatrixDropTarget(target) {",
  "  if (matrixDropTarget === target) return;",
  '  if (matrixDropTarget) matrixDropTarget.closest(".area--quadrant").classList.remove("drop-target");',
  "  matrixDropTarget = target;",
  '  if (matrixDropTarget) matrixDropTarget.closest(".area--quadrant").classList.add("drop-target");',
  "}",
  "function clearMatrixDnd() {",
  '  if (matrixDraggingCard) matrixDraggingCard.classList.remove("dragging");',
  "  setMatrixDropTarget(null);",
  "  matrixDraggingCard = null;",
  "}",
  "function setMatrixDndPending(pending) {",
  "  matrixDndPending = pending;",
  '  document.querySelectorAll(".matrix-cards .task-card").forEach(function (card) {',
  '    card.setAttribute("draggable", pending ? "false" : "true");',
  "  });",
  "}",
  "function persistMatrixDrop(card, target) {",
  '  var taskId = card.getAttribute("data-task-id");',
  '  var version = card.getAttribute("data-version");',
  '  var area = target.getAttribute("data-area");',
  "  var order = matrixCards(target).indexOf(card);",
  "  if (!taskId || !version || area === null || order < 0) return;",
  "  setMatrixDndPending(true);",
  '  return fetch("/api/tasks/reorder", {',
  '    method: "POST",',
  '    headers: { "Content-Type": "application/json" },',
  "    body: JSON.stringify({ id: taskId, area: Number(area), order: order, version: Number(version) }),",
  "  }).then(function (response) {",
  "    if (!response.ok) { showDndConflict(); restoreMatrix(); return null; }",
  "    return response.json();",
  "  }).then(function (tasks) {",
  "    if (!Array.isArray(tasks)) return;",
  "    tasks.forEach(function (task) {",
  '      if (!task || typeof task.id !== "string" || typeof task.version !== "number") return;',
  '      document.querySelectorAll(".task-card[data-task-id]").forEach(function (updatedCard) {',
  '        if (updatedCard.getAttribute("data-task-id") === task.id) {',
  '          updatedCard.setAttribute("data-version", String(task.version));',
  "        }",
  "      });",
  "    });",
  "  }).finally(function () { setMatrixDndPending(false); });",
  "}",
  "function initMatrixDnd() {",
  '  var lists = document.querySelectorAll(".matrix-cards[data-dnd-group]");',
  "  lists.forEach(function (list) {",
  '    list.querySelectorAll(".task-card").forEach(function (card) {',
  '      card.setAttribute("draggable", matrixDndPending ? "false" : "true");',
  "    });",
  "  });",
  "}",
  'document.addEventListener("dragstart", function (event) {',
  '  var card = event.target.closest(".matrix-cards .task-card");',
  "  if (!card || !event.dataTransfer) return;",
  "  if (matrixDndPending) { event.preventDefault(); return; }",
  "  matrixDraggingCard = card;",
  '  event.dataTransfer.setData("text/plain", card.getAttribute("data-task-id") || "");',
  '  event.dataTransfer.effectAllowed = "move";',
  '  card.classList.add("dragging");',
  "});",
  'document.addEventListener("dragover", function (event) {',
  '  var target = event.target.closest(".matrix-cards[data-dnd-group]");',
  "  if (!matrixDraggingCard || !target) return;",
  "  event.preventDefault();",
  '  event.dataTransfer.dropEffect = "move";',
  "  setMatrixDropTarget(target);",
  "});",
  'document.addEventListener("drop", function (event) {',
  '  var target = event.target.closest(".matrix-cards[data-dnd-group]");',
  "  if (!matrixDraggingCard || !target) return;",
  "  event.preventDefault();",
  "  var card = matrixDraggingCard;",
  "  var index = matrixDropIndex(target, event.clientY);",
  "  var cards = matrixCards(target).filter(function (candidate) { return candidate !== card; });",
  "  target.insertBefore(card, cards[index] || null);",
  "  suppressMatrixCardClick = true;",
  "  persistMatrixDrop(card, target);",
  "  clearMatrixDnd();",
  "});",
  'document.addEventListener("dragend", clearMatrixDnd);',
  'document.addEventListener("click", function (event) {',
  '  if (!suppressMatrixCardClick || !event.target.closest(".matrix-cards .task-card")) return;',
  "  event.preventDefault();",
  "  suppressMatrixCardClick = false;",
  "}, true);",
  'document.addEventListener("DOMContentLoaded", initMatrixDnd);',
  'document.addEventListener("htmx:load", initMatrixDnd);',
].join("\n");

export const Layout: FC<{ active: "matrix" | "tasks"; children?: JSX.Element }> = ({
  active,
  children,
}) => (
  <html lang="ja">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>SIFTQ</title>
      <link rel="stylesheet" href="/styles.css" />
      <script src={HTMX_SCRIPT} defer></script>
      <script src="/matrix-dnd.js" defer></script>
    </head>
    <body>
      <header class="topbar">
        <a class="brand" href="/">SIFTQ</a>
        <nav class="nav" aria-label="Primary">
          <a class={active === "matrix" ? "active" : undefined} href="/">
            Matrix
          </a>
          <a class={active === "tasks" ? "active" : undefined} href="/tasks">
            Tasks
          </a>
        </nav>
      </header>
      <main id="page">{children}</main>
      <script>{HTMX_CONFLICT_SWAP_SCRIPT}</script>
      <script>{POPOVER_DISMISS_SCRIPT}</script>
    </body>
  </html>
);
