export const IDEAS_CSS = `
.page--ideas {
  background: #30363d;
  color: #f1f3f4;
  max-width: none;
  min-height: calc(100vh - 63px);
  padding: 48px 16px;
}

.page--ideas-empty {
  display: flex;
  flex-direction: column;
}

.ideas-header {
}

.ideas-composer {
  background: #e6e9ee;
  border: 1px solid #8b949e;
  border-radius: 6px;
  box-shadow: 0 1px 2px rgb(31 35 40 / 8%);
  color: #57606a;
  margin: 0 auto 28px;
  width: min(100%, 1008px);
}

.ideas-composer__trigger {
  align-items: center;
  background: transparent;
  border: 0;
  color: inherit;
  cursor: text;
  display: flex;
  font: inherit;
  font-size: 14px;
  justify-content: space-between;
  min-height: 48px;
  padding: 0 16px;
  text-align: left;
  width: 100%;
}

.ideas-composer__line {
  border-bottom: 2px solid #57606a;
  border-top: 2px solid #57606a;
  height: 8px;
  opacity: 0.7;
  width: 18px;
}

.ideas-composer--open {
  background: #e6e9ee;
  border: 1px solid #8b949e;
  box-shadow: 0 1px 3px rgb(31 35 40 / 8%);
  padding: 0;
}

.ideas-composer--open .ideas-composer__trigger {
  display: none;
}

.ideas-composer__editor {
  display: grid;
  gap: 12px;
  padding: 16px;
}

.ideas-composer__editor[hidden] {
  display: none;
}

.ideas-composer__title,
.ideas-composer__description {
  background: transparent;
  border: 0;
  color: #24292f;
  font: inherit;
  outline: 0;
  padding: 0;
  width: 100%;
}

.ideas-composer__title {
  font-size: 17px;
  font-weight: 700;
  line-height: 1.4;
}

.ideas-composer__description {
  line-height: 1.55;
  max-height: 320px;
  min-height: 24px;
  overflow-y: auto;
  resize: none;
}

.ideas-composer__title:focus,
.ideas-composer__description:focus {
  box-shadow: 0 2px 0 #0969da;
}

.ideas-composer__actions {
  display: flex;
  justify-content: flex-end;
}

.ideas-composer__close {
  background: transparent;
  border: 0;
  border-radius: 6px;
  color: #57606a;
  cursor: pointer;
  font: inherit;
  padding: 8px 16px;
}

.ideas-composer__close:hover,
.ideas-composer__close:focus-visible {
  background: #f6f8fa;
  color: #0969da;
}

.ideas-grid {
  align-items: start;
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(1, minmax(0, 1fr));
  margin-inline: auto;
  position: relative;
  width: 100%;
}

.ideas-group-gap {
  height: 24px;
  margin: 16px 0;
}

.ideas-grid.masonry-ready {
  display: block;
  min-height: 0;
}

.idea-card {
  background: #e6e9ee;
  border: 1px solid #8b949e;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgb(31 35 40 / 8%);
  display: flex;
  flex-direction: column;
  position: relative;
  width: auto;
  padding: 16px;
  transition: border-color 120ms ease, box-shadow 120ms ease, transform 120ms ease;
}

.idea-card:nth-child(3n + 2) {
  background: #dfe3e8;
}

.idea-card:nth-child(3n + 3) {
  background: #eceef2;
}

.idea-card:hover {
  border-color: #0969da;
  box-shadow: 0 4px 12px rgb(31 35 40 / 14%);
  transform: translateY(-1px);
}

.idea-card[draggable="true"] {
  cursor: grab;
}

.idea-card.dragging {
  cursor: grabbing;
  opacity: 0.45;
}

.idea-card.drop-target {
  border-color: #0969da;
}

.idea-card__link {
  column-gap: 8px;
  color: inherit;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  text-decoration: none;
}

.idea-card__pin {
  cursor: pointer;
  display: block;
  fill: #ffffff;
  grid-column: 1;
  height: 18px;
  stroke: #24292f;
  stroke-width: 1.5;
  width: 18px;
}

.idea-card[data-pinned="true"] .idea-card__pin {
  fill: #24292f;
  stroke: none;
}

.idea-card h2 {
  color: #24292f;
  font-size: 17px;
  line-height: 1.4;
  grid-column: 2;
  margin: 0;
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.idea-card__description {
  border-top: 1px solid #8b949e;
  color: #57606a;
  font-size: 14px;
  grid-column: 1 / -1;
  line-height: 1.55;
  margin: 12px 0 0;
  padding-top: 12px;
  white-space: pre-wrap;
}

.idea-card__description--empty {
  border-top: 0;
  font-style: italic;
  padding-top: 0;
}

.ideas-grid.masonry-ready > .idea-card {
  margin: 0;
  position: absolute;
}

.idea-card__footer {
  align-items: center;
  bottom: 16px;
  color: #57606a;
  display: flex;
  font-size: 11px;
  justify-content: flex-end;
  margin: 0;
  opacity: 0;
  padding-top: 0;
  position: absolute;
  right: 16px;
  transition: opacity 120ms ease;
}

.idea-card:hover .idea-card__footer,
.idea-card:focus-within .idea-card__footer {
  opacity: 1;
}

.idea-card__more {
  background: transparent;
  border: 0;
  border-radius: 50%;
  cursor: pointer;
  height: 28px;
  position: relative;
  width: 28px;
}

.idea-card__more:hover {
  background: #d0d7de;
}

.idea-card__more span,
.idea-card__more span::before,
.idea-card__more span::after {
  background: #57606a;
  border-radius: 50%;
  content: "";
  height: 3px;
  left: 13px;
  position: absolute;
  top: 13px;
  width: 3px;
}

.idea-card__more span::before {
  left: -7px;
  top: 0;
}

.idea-card__more span::after {
  left: 7px;
  top: 0;
}

.ideas-empty {
  background: #e6e9ee;
  border: 1px dashed #8b949e;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgb(31 35 40 / 8%);
  color: #24292f;
  align-items: center;
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: center;
  margin: 0 auto;
  min-height: 240px;
  padding: 56px 24px;
  text-align: center;
  width: min(100%, 1008px);
}

.ideas-empty h2 {
  font-size: 18px;
  margin: 0;
}

.ideas-empty p {
  margin: 0;
}

.page--idea-detail {
  background: #30363d;
  max-width: none;
  min-height: calc(100vh - 63px);
  padding: 24px 5vw 48px;
}

.idea-detail__header {
  align-items: center;
  display: flex;
  gap: 16px;
  margin-bottom: 32px;
}

.idea-detail__title {
  background: transparent;
  border: 0;
  color: #24292f;
  flex: 1;
  font-size: 22px;
  font-weight: 700;
  line-height: 1.3;
  outline: 0;
  padding: 0;
}

.idea-detail__title:focus {
  box-shadow: 0 2px 0 #0969da;
}

.idea-detail__pin {
  align-items: center;
  background: transparent;
  border: 0;
  color: #24292f;
  cursor: pointer;
  display: inline-flex;
  flex: 0 0 auto;
  height: 36px;
  justify-content: center;
  padding: 6px;
  width: 36px;
}

.idea-detail__pin svg {
  fill: currentColor;
  height: 22px;
  stroke: none;
  width: 22px;
}

.idea-detail__pin[aria-pressed="true"] {
  color: #24292f;
}

.idea-detail__pin[aria-pressed="false"] {
  color: #ffffff;
}

.idea-detail__pin[aria-pressed="false"] svg {
  stroke: #24292f;
  stroke-width: 1.5;
}

.idea-detail__close {
  align-items: center;
  background: transparent;
  border: 0;
  border-radius: 6px;
  color: #57606a;
  display: inline-flex;
  font: inherit;
  justify-content: center;
  min-width: 80px;
  padding: 8px 16px;
  text-decoration: none;
}

.idea-detail-modal {
  background: #e6e9ee;
  color: #24292f;
  border: 0;
  border-radius: 8px;
  max-height: calc(100vh - 48px);
  max-width: 720px;
  padding: 0;
  width: calc(100vw - 32px);
}

.idea-detail-modal::backdrop {
  background: rgb(31 35 40 / 65%);
}

.idea-detail-modal .idea-detail__form {
  background: #e6e9ee;
  border: 0;
  border-radius: 0;
  box-shadow: none;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  padding-bottom: 8px;
}

.idea-detail__actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.idea-detail__close:hover,
.idea-detail__close:focus-visible {
  background: #f6f8fa;
  color: #0969da;
}

.idea-detail__form {
  background: #e6e9ee;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgb(31 35 40 / 8%);
  padding: 24px;
}

.idea-detail__description {
  background: transparent;
  border: 0;
  border-top: 1px solid #8b949e;
  box-shadow: none;
  line-height: 1.55;
  max-height: calc(100vh - 180px);
  min-height: 240px;
  outline: 0;
  overflow-y: auto;
  padding: 12px 0 0;
  white-space: pre-wrap;
  width: 100%;
}

.idea-detail__description--empty {
  border-top: 0;
  padding-top: 0;
}

.idea-detail__description a {
  color: #0969da;
  text-decoration: underline;
}

@media (width < 40rem) {
  .page--ideas {
    padding: 24px 16px 32px;
  }

  .page--idea-detail {
    padding: 16px;
  }

  .ideas-header {
    flex-direction: column;
    margin-bottom: 20px;
  }

  .ideas-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    width: 100%;
  }

  .idea-card {
    width: auto;
  }
}

@media (width < 22.5rem) {
  .ideas-grid {
    grid-template-columns: 1fr;
  }
}

@media (width >= 40rem) and (width < 56rem) {
  .ideas-grid {
    grid-template-columns: repeat(2, 240px);
    width: 496px;
  }
}

@media (width >= 56rem) and (width < 72rem) {
  .ideas-grid {
    grid-template-columns: repeat(3, 240px);
    width: 752px;
  }
}

@media (width >= 72rem) and (width < 90rem) {
  .ideas-grid {
    grid-template-columns: repeat(4, 240px);
    width: 1008px;
  }
}

@media (width >= 90rem) and (width < 110rem) {
  .ideas-grid {
    grid-template-columns: repeat(5, 240px);
    width: 1264px;
  }
}

@media (width >= 97rem) and (width < 113rem) {
  .ideas-grid {
    grid-template-columns: repeat(6, 240px);
    width: 1520px;
  }
}

@media (width >= 113rem) and (width < 129rem) {
  .ideas-grid {
    grid-template-columns: repeat(7, 240px);
    width: 1776px;
  }
}

@media (width >= 129rem) {
  .ideas-grid {
    grid-template-columns: repeat(8, 240px);
    width: 2032px;
  }
}
`;
