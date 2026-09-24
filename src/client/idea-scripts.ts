export const IDEAS_DND_SCRIPT = `
var ideasDraggingCard = null;
function ideasCardFromEvent(event) {
  var target = event.target;
  return target && target.closest ? target.closest(".ideas-grid > .idea-card") : null;
}
function ideasSameGroup(left, right) {
  return left && right && left.getAttribute("data-pinned") === right.getAttribute("data-pinned");
}
function clearIdeasDrag() {
  if (ideasDraggingCard) ideasDraggingCard.classList.remove("dragging");
  document.querySelectorAll(".ideas-grid .drop-target").forEach(function (card) { card.classList.remove("drop-target"); });
  ideasDraggingCard = null;
}
document.addEventListener("dragstart", function (event) {
  var card = ideasCardFromEvent(event);
  if (!card || !event.dataTransfer) return;
  ideasDraggingCard = card;
  card.classList.add("dragging");
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", card.getAttribute("data-idea-id") || "");
});
document.addEventListener("dragover", function (event) {
  if (!ideasDraggingCard || !event.dataTransfer) return;
  var target = ideasCardFromEvent(event);
  if (!target || target === ideasDraggingCard || !ideasSameGroup(ideasDraggingCard, target)) return;
  event.preventDefault();
  event.dataTransfer.dropEffect = "move";
  document.querySelectorAll(".ideas-grid .drop-target").forEach(function (card) { card.classList.remove("drop-target"); });
  target.classList.add("drop-target");
  var box = target.getBoundingClientRect();
  if (event.clientY < box.top + box.height / 2) target.before(ideasDraggingCard);
  else target.after(ideasDraggingCard);
  if (typeof layoutIdeaMasonry === "function") layoutIdeaMasonry();
});
document.addEventListener("drop", function (event) {
  if (!ideasDraggingCard) return;
  var target = ideasCardFromEvent(event);
  if (target && ideasSameGroup(ideasDraggingCard, target)) {
    event.preventDefault();
    persistIdeaOrders();
  }
});
document.addEventListener("dragend", clearIdeasDrag);
document.addEventListener("DOMContentLoaded", clearIdeasDrag);
document.addEventListener("htmx:load", clearIdeasDrag);
`;

export const IDEA_DETAIL_SCRIPT = `
function ideaApi(path, init) {
  return fetch(path, Object.assign({ headers: { "content-type": "application/json" } }, init || {})).then(function (response) {
    if (!response.ok) throw new Error("Idea request failed: " + response.status);
    return response.status === 204 ? null : response.json();
  });
}
function ideaCardId(card) { return card.getAttribute("data-idea-id"); }
function ideaCardOrder(card) { var order = Number(card.getAttribute("data-idea-order")); return Number.isFinite(order) ? order : 0; }
function setIdeaCardOrder(card, order) { card.setAttribute("data-idea-order", String(order)); card.setAttribute("data-order", String(order)); }
function ideaCardById(id) {
  var found = null;
  document.querySelectorAll(".idea-card[data-idea-id]").forEach(function (card) { if (!found && ideaCardId(card) === id) found = card; });
  return found;
}
function ideaFormPinned(form) { return form.getAttribute("data-idea-pinned") === "true"; }
function ideaFields(form) { return { title: form.querySelector('input[name="title"]'), description: form.querySelector('textarea[name="description"]') }; }
function updateIdeaPinButton(form) {
  var button = form.querySelector("[data-idea-pin]");
  if (button) { button.setAttribute("aria-pressed", ideaFormPinned(form) ? "true" : "false"); button.setAttribute("aria-label", ideaFormPinned(form) ? "Unpin idea" : "Pin idea"); }
}
function resizeIdeaDescription(form) {
  var description = form.querySelector(".idea-detail__description");
  if (!description) return;
  description.style.height = "auto";
  description.style.height = description.scrollHeight + "px";
}
function layoutIdeaMasonryGrid(grid) {
  var cards = Array.prototype.slice.call(grid.querySelectorAll(":scope > .idea-card"));
  grid.classList.remove("masonry-ready");
  grid.style.height = "";
  cards.forEach(function (card) { card.style.left = ""; card.style.top = ""; card.style.width = ""; });
  if (cards.length === 0) return;
  var columns = getComputedStyle(grid).gridTemplateColumns.trim().split(/\\s+/).length;
  var gap = 16;
  var columnWidth = (grid.clientWidth - gap * (columns - 1)) / columns;
  cards.forEach(function (card) { card.style.width = columnWidth + "px"; });
  grid.classList.add("masonry-ready");
  var heights = Array(columns).fill(0);
  cards.forEach(function (card) {
    var column = heights.indexOf(Math.min.apply(null, heights));
    card.style.left = column * (columnWidth + gap) + "px";
    card.style.top = heights[column] + "px";
    heights[column] += card.offsetHeight + gap;
  });
  grid.style.height = Math.max.apply(null, heights) - gap + "px";
}
function layoutIdeaMasonry() { document.querySelectorAll(".ideas-grid").forEach(layoutIdeaMasonryGrid); }
function updateIdeaGroups() {
  var pinnedGrid = document.querySelector('.ideas-grid[data-idea-group="pinned"]');
  var unpinnedGrid = document.querySelector('.ideas-grid[data-idea-group="unpinned"]');
  if (!pinnedGrid || !unpinnedGrid) return;
  var cards = Array.prototype.slice.call(document.querySelectorAll(".ideas-grid > .idea-card"));
  cards.sort(function (left, right) { return ideaCardOrder(left) - ideaCardOrder(right); });
  cards.filter(function (card) { return card.getAttribute("data-pinned") === "true"; }).forEach(function (card) { pinnedGrid.appendChild(card); });
  cards.filter(function (card) { return card.getAttribute("data-pinned") !== "true"; }).forEach(function (card) { unpinnedGrid.appendChild(card); });
  var gap = document.querySelector("[data-idea-group-gap]");
  if (gap) gap.hidden = pinnedGrid.children.length === 0 || unpinnedGrid.children.length === 0;
  var empty = document.querySelector("[data-ideas-empty]");
  if (empty) empty.hidden = cards.length > 0;
  layoutIdeaMasonry();
}
function normalizeIdeaGroupOrder(grid) {
  if (!grid) return;
  grid.querySelectorAll(":scope > .idea-card").forEach(function (card, index) { setIdeaCardOrder(card, index + 1); });
}
function persistIdeaOrders() {
  var updates = [];
  document.querySelectorAll('.ideas-grid[data-idea-group="pinned"], .ideas-grid[data-idea-group="unpinned"]').forEach(function (grid) {
    normalizeIdeaGroupOrder(grid);
    grid.querySelectorAll(":scope > .idea-card").forEach(function (card) { updates.push({ id: ideaCardId(card), order: ideaCardOrder(card) }); });
  });
  ideaApi("/api/ideas/reorder", { method: "POST", body: JSON.stringify({ ideas: updates }) }).catch(function () {});
}
function updateIdeaCardPin(card, pinned) {
  card.setAttribute("data-pinned", pinned ? "true" : "false");
  var pin = card.querySelector(".idea-card__pin");
  if (pin) pin.setAttribute("aria-label", pinned ? "Pinned" : "Not pinned");
}
function nextIdeaOrder(grid) {
  var max = 0;
  if (grid) grid.querySelectorAll(":scope > .idea-card").forEach(function (card) { max = Math.max(max, ideaCardOrder(card)); });
  return max + 1;
}
function moveIdeaCardToGroup(card, pinned) {
  var current = card.getAttribute("data-pinned") === "true";
  if (current === pinned) return;
  var grid = document.querySelector('.ideas-grid[data-idea-group="' + (pinned ? "pinned" : "unpinned") + '"]');
  if (grid) setIdeaCardOrder(card, nextIdeaOrder(grid));
}
function syncIdeaCard(form) {
  var card = ideaCardById(form.getAttribute("data-idea-id"));
  if (!card) return;
  var fields = ideaFields(form);
  var title = card.querySelector("h2");
  var description = card.querySelector(".idea-card__description");
  if (title && fields.title) title.textContent = fields.title.value;
  if (description && fields.description) { description.textContent = fields.description.value || "No description yet."; description.classList.toggle("idea-card__description--empty", !fields.description.value); }
  updateIdeaCardPin(card, ideaFormPinned(form));
  updateIdeaGroups();
}
function saveIdeaDraft(form) {
  var fields = ideaFields(form);
  var title = fields.title ? fields.title.value.trim() : "";
  if (!title) return;
  var description = fields.description ? fields.description.value : "";
  var body = { title: title, description: description, pinned: ideaFormPinned(form), order: Number(form.getAttribute("data-idea-order")) };
  syncIdeaCard(form);
 ideaApi("/api/ideas/" + encodeURIComponent(form.getAttribute("data-idea-id") || ""), { method: "PATCH", body: JSON.stringify(body), keepalive: true }).then(function (idea) {
    if (idea && typeof idea.order === "number") form.setAttribute("data-idea-order", String(idea.order));
    persistIdeaOrders();
  }).catch(function () {});
}
function scheduleIdeaDraftSave(form) {
  if (form._ideaDraftTimer) clearTimeout(form._ideaDraftTimer);
  form._ideaDraftTimer = setTimeout(function () { saveIdeaDraft(form); }, 400);
}
function setIdeaPinned(form, pinned) {
  form.setAttribute("data-idea-pinned", pinned ? "true" : "false");
  var card = ideaCardById(form.getAttribute("data-idea-id"));
  if (card) { moveIdeaCardToGroup(card, pinned); updateIdeaCardPin(card, pinned); form.setAttribute("data-idea-order", card.getAttribute("data-idea-order") || ""); }
  updateIdeaPinButton(form);
  saveIdeaDraft(form);
}
function toggleIdeaCardPin(card) {
  var pinned = card.getAttribute("data-pinned") !== "true";
  var grid = document.querySelector('.ideas-grid[data-idea-group="' + (pinned ? "pinned" : "unpinned") + '"]');
  if (grid) setIdeaCardOrder(card, nextIdeaOrder(grid));
  updateIdeaCardPin(card, pinned);
  updateIdeaGroups();
  ideaApi("/api/ideas/" + encodeURIComponent(ideaCardId(card)), { method: "PATCH", body: JSON.stringify({ pinned: pinned, order: ideaCardOrder(card) }) }).then(function () { persistIdeaOrders(); }).catch(function () {});
}
function createIdeaCard(idea) {
  var card = document.createElement("article");
  card.className = "idea-card";
  card.setAttribute("data-idea-id", idea.id);
  card.setAttribute("data-idea-order", idea.order);
  card.setAttribute("data-order", idea.order);
  card.setAttribute("data-pinned", idea.pinned ? "true" : "false");
  card.setAttribute("draggable", "true");
  var link = document.createElement("a");
  link.className = "idea-card__link";
  link.href = "/ideas/" + encodeURIComponent(idea.id);
  var pin = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  pin.setAttribute("class", "idea-card__pin"); pin.setAttribute("role", "img"); pin.setAttribute("aria-label", idea.pinned ? "Pinned" : "Not pinned"); pin.setAttribute("viewBox", "0 0 24 24");
  var path = document.createElementNS("http://www.w3.org/2000/svg", "path"); path.setAttribute("d", "M16 12V4h1V2H7v2h1v8l-2 2v2h5.8v6h2.4v-6H20v-2z"); pin.appendChild(path); link.appendChild(pin);
  var title = document.createElement("h2"); title.textContent = idea.title; link.appendChild(title);
  var description = document.createElement("p"); description.className = idea.description ? "idea-card__description" : "idea-card__description idea-card__description--empty"; description.textContent = idea.description || "No description yet."; link.appendChild(description);
  card.appendChild(link);
  var footer = document.createElement("footer"); footer.className = "idea-card__footer";
  var more = document.createElement("button"); more.type = "button"; more.className = "idea-card__more"; more.setAttribute("aria-label", "More options for " + idea.title); var dots = document.createElement("span"); dots.setAttribute("aria-hidden", "true"); more.appendChild(dots); footer.appendChild(more); card.appendChild(footer);
  return card;
}
function createNewIdea(title, description) {
  if (!title && !description) return;
  ideaApi("/api/ideas", { method: "POST", body: JSON.stringify({ title: title || "無題", description: description }) }).then(function (idea) {
    var grid = document.querySelector('.ideas-grid[data-idea-group="unpinned"]');
    if (grid) grid.appendChild(createIdeaCard(idea));
    updateIdeaGroups();
  }).catch(function () {});
}
var ideaMenu = null;
var ideaMenuCard = null;
var ideaDeleteModal = null;
function closeIdeaMenu() { if (ideaMenu) ideaMenu.remove(); ideaMenu = null; ideaMenuCard = null; }
function closeIdeaDeleteModal() { if (ideaDeleteModal) ideaDeleteModal.remove(); ideaDeleteModal = null; }
function removeIdeaCard(card) {
  var id = ideaCardId(card);
  if (!id) return;
  ideaApi("/api/ideas/" + encodeURIComponent(id), { method: "DELETE" }).then(function () { card.remove(); updateIdeaGroups(); persistIdeaOrders(); }).catch(function () {});
}
function renderIdeaDeleteModal(card) {
  var backdrop = document.createElement("div"); backdrop.className = "matrix-modal-backdrop";
  var dialog = document.createElement("div"); dialog.className = "matrix-modal";
  var message = document.createElement("p"); message.className = "matrix-modal-text"; message.textContent = "このメモを削除しますか？"; dialog.appendChild(message);
  var row = document.createElement("div"); row.className = "matrix-modal-actions";
  ["cancel", "confirm"].forEach(function (action) { var button = document.createElement("button"); button.type = "button"; button.className = action === "confirm" ? "matrix-modal-button matrix-modal-button--danger" : "matrix-modal-button matrix-modal-button--cancel"; button.textContent = action === "confirm" ? "削除" : "キャンセル"; button.setAttribute("data-idea-modal-action", action); row.appendChild(button); });
  dialog.appendChild(row);
  backdrop.addEventListener("click", function (event) { var button = event.target.closest ? event.target.closest("[data-idea-modal-action]") : null; if (!button) return; if (button.getAttribute("data-idea-modal-action") === "confirm") { closeIdeaDeleteModal(); removeIdeaCard(card); } else closeIdeaDeleteModal(); });
  backdrop.appendChild(dialog); document.body.appendChild(backdrop); ideaDeleteModal = backdrop;
}
function openIdeaMenu(card, button) {
  closeIdeaMenu(); ideaMenuCard = card; var menu = document.createElement("div"); menu.className = "matrix-menu";
  var deleteButton = document.createElement("button"); deleteButton.type = "button"; deleteButton.className = "matrix-menu-item matrix-menu-item--delete"; deleteButton.textContent = "削除"; deleteButton.setAttribute("data-idea-action", "delete"); menu.appendChild(deleteButton);
  menu.addEventListener("click", function (event) { var item = event.target.closest("[data-idea-action]"); if (item && item.getAttribute("data-idea-action") === "delete") { var target = ideaMenuCard; closeIdeaMenu(); renderIdeaDeleteModal(target); } });
  document.body.appendChild(menu); var rect = button.getBoundingClientRect(); var menuRect = menu.getBoundingClientRect(); menu.style.left = Math.max(8, Math.min(rect.left, window.innerWidth - menuRect.width - 8)) + "px"; menu.style.top = Math.max(8, Math.min(rect.bottom + 4, window.innerHeight - menuRect.height - 8)) + "px"; ideaMenu = menu;
}
function setIdeaComposerOpen(composer, open) { var trigger = composer.querySelector("[data-idea-composer-trigger]"); var editor = composer.querySelector("[data-idea-composer-editor]"); composer.classList.toggle("ideas-composer--open", open); composer.setAttribute("data-idea-composer-open", open ? "true" : "false"); if (trigger) trigger.setAttribute("aria-expanded", open ? "true" : "false"); if (editor) editor.hidden = !open; if (open) { var title = composer.querySelector(".ideas-composer__title"); if (title) title.focus(); } }
function finishIdeaComposer(composer) { var title = composer.querySelector(".ideas-composer__title"); var description = composer.querySelector(".ideas-composer__description"); createNewIdea(title ? title.value.trim() : "", description ? description.value.trim() : ""); if (title) title.value = ""; if (description) description.value = ""; setIdeaComposerOpen(composer, false); }
function openIdeaModal(card) {
  var modalForm = document.querySelector("[data-idea-modal] form[data-idea-form]");
  if (!modalForm) return;
  modalForm.setAttribute("data-idea-id", ideaCardId(card)); modalForm.setAttribute("data-idea-order", card.getAttribute("data-idea-order") || ""); modalForm.setAttribute("data-idea-pinned", card.getAttribute("data-pinned") === "true" ? "true" : "false");
  var fields = ideaFields(modalForm); var title = card.querySelector("h2"); var description = card.querySelector(".idea-card__description"); if (fields.title) fields.title.value = title ? title.textContent || "" : ""; if (fields.description) fields.description.value = description ? description.textContent || "" : ""; updateIdeaPinButton(modalForm); resizeIdeaDescription(modalForm); var dialog = document.querySelector("[data-idea-modal]"); if (dialog && typeof dialog.showModal === "function") dialog.showModal();
}
function initializeIdeaDetails() {
  document.querySelectorAll("[data-idea-composer]").forEach(function (composer) { if (composer.dataset.ideaComposerInitialized === "true") return; composer.dataset.ideaComposerInitialized = "true"; setIdeaComposerOpen(composer, false); var trigger = composer.querySelector("[data-idea-composer-trigger]"); var close = composer.querySelector("[data-idea-composer-close]"); if (trigger) trigger.addEventListener("click", function () { setIdeaComposerOpen(composer, true); }); if (close) close.addEventListener("click", function () { finishIdeaComposer(composer); }); composer.addEventListener("keydown", function (event) { if (!event.ctrlKey || event.key !== "Enter") return; var target = event.target; if (!target || !target.closest || !target.closest(".ideas-composer__title, .ideas-composer__description")) return; event.preventDefault(); finishIdeaComposer(composer); }); document.addEventListener("click", function (event) { if (composer.getAttribute("data-idea-composer-open") === "true" && !event.target.closest("[data-idea-composer]")) finishIdeaComposer(composer); }); });
  document.querySelectorAll("form[data-idea-form]").forEach(function (form) { if (form.dataset.ideaDetailInitialized === "true") return; form.dataset.ideaDetailInitialized = "true"; updateIdeaPinButton(form); resizeIdeaDescription(form); form.addEventListener("input", function () { resizeIdeaDescription(form); scheduleIdeaDraftSave(form); }); var pin = form.querySelector("[data-idea-pin]"); if (pin) pin.addEventListener("click", function () { setIdeaPinned(form, !ideaFormPinned(form)); }); var close = form.querySelector("[data-idea-close]"); if (close) close.addEventListener("click", function () { saveIdeaDraft(form); }); });
}
document.addEventListener("DOMContentLoaded", initializeIdeaDetails);
document.addEventListener("htmx:load", initializeIdeaDetails);
window.addEventListener("resize", layoutIdeaMasonry);
document.addEventListener("click", function (event) {
  if (ideaMenu && !ideaMenu.contains(event.target)) closeIdeaMenu();
  var modal = document.querySelector("[data-idea-modal]"); if (modal && modal.open) return;
  var card = event.target.closest ? event.target.closest(".idea-card[data-idea-id]") : null; if (!card) return;
  var more = event.target.closest(".idea-card__more"); if (more) { event.preventDefault(); openIdeaMenu(card, more); return; }
  if (event.target.closest(".idea-card__pin")) { event.preventDefault(); toggleIdeaCardPin(card); return; }
  event.preventDefault();
   openIdeaModal(card);
});
`;
