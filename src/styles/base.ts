export const BASE_CSS = `
:root {
  color: #1b1f24;
  background: #3b434d;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
}

::selection {
  background: #444444;
  color: #ffffff;
}

:focus-visible {
  box-shadow: 0 0 0 4px #e6e9ee;
  outline: 2px solid #0f4d24;
  outline-offset: 2px;
}

.matrix-cards,
.description-editor,
.ideas-composer__description,
.idea-detail-modal .idea-detail__form,
.idea-detail__description {
  scrollbar-color: #8b949e transparent;
  scrollbar-width: thin;
}

.matrix-cards::-webkit-scrollbar,
.description-editor::-webkit-scrollbar,
.ideas-composer__description::-webkit-scrollbar,
.idea-detail-modal .idea-detail__form::-webkit-scrollbar,
.idea-detail__description::-webkit-scrollbar {
  height: 8px;
  width: 8px;
}

.matrix-cards::-webkit-scrollbar-track,
.description-editor::-webkit-scrollbar-track,
.ideas-composer__description::-webkit-scrollbar-track,
.idea-detail-modal .idea-detail__form::-webkit-scrollbar-track,
.idea-detail__description::-webkit-scrollbar-track {
  background: transparent;
}

.matrix-cards::-webkit-scrollbar-button,
.description-editor::-webkit-scrollbar-button,
.ideas-composer__description::-webkit-scrollbar-button,
.idea-detail-modal .idea-detail__form::-webkit-scrollbar-button,
.idea-detail__description::-webkit-scrollbar-button {
  display: none;
}

.matrix-cards::-webkit-scrollbar-thumb,
.description-editor::-webkit-scrollbar-thumb,
.ideas-composer__description::-webkit-scrollbar-thumb,
.idea-detail-modal .idea-detail__form::-webkit-scrollbar-thumb,
.idea-detail__description::-webkit-scrollbar-thumb {
  background: transparent;
  background-clip: content-box;
  border: 2px solid transparent;
  border-radius: 999px;
}

.matrix-cards:hover::-webkit-scrollbar-thumb,
.description-editor:hover::-webkit-scrollbar-thumb,
.ideas-composer__description:hover::-webkit-scrollbar-thumb,
.idea-detail-modal .idea-detail__form:hover::-webkit-scrollbar-thumb,
.idea-detail__description:hover::-webkit-scrollbar-thumb,
.matrix-cards:focus-within::-webkit-scrollbar-thumb,
.description-editor:focus-within::-webkit-scrollbar-thumb,
.ideas-composer__description:focus-within::-webkit-scrollbar-thumb,
.idea-detail-modal .idea-detail__form:focus-within::-webkit-scrollbar-thumb,
.idea-detail__description:focus-within::-webkit-scrollbar-thumb {
  background: #8b949e;
}

a {
  color: inherit;
  text-decoration: none;
}

.shell {
  min-height: 100vh;
}

.topbar {
  align-items: center;
  background: #e6e9ee;
  border-bottom: 1px solid #8b949e;
  display: flex;
  gap: 16px;
  justify-content: flex-start;
  padding: 14px 20px;
  flex-wrap: wrap;
}

.brand {
  font-size: 18px;
  font-weight: 700;
}

.nav {
  display: flex;
  gap: 8px;
}

.logout {
  margin: 0 0 0 auto;
}

.nav a,
.button {
  background: #c1c9d3;
  border: 1px solid #8b949e;
  border-radius: 6px;
  display: inline-flex;
  font-size: 14px;
  font-weight: 600;
  min-height: 34px;
  padding: 7px 12px;
}

.nav .active,
.button.primary {
  background: #1f883d;
  border-color: #2a9147;
  color: #ffffff;
}

.page {
  margin: 0 auto;
  max-width: 1180px;
  padding: 24px;
}

.page--matrix {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  height: calc(100vh - 63px);
  max-width: none;
  padding: 3vh 5vw;
  row-gap: 18px;
  width: 100%;
}

.page--matrix > * {
  justify-self: center;
  width: min(100%, 80vw);
}

.task-status-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 18px;
}

.task-status-filter .button.small {
  min-height: 32px;
  padding: 5px 12px;
}

.task-status-filter .button.is-active {
  background: #1f883d;
  border-color: #2a9147;
  color: #ffffff;
}

.task-status-filter--toolbar {
  margin-bottom: 0;
}

.task-status-filter[hidden],
.task-selection-summary[hidden] {
  display: none;
}

.task-selection-summary {
  align-items: center;
  color: #1b1f24;
  display: flex;
  font-size: 14px;
  font-weight: 600;
  min-height: 32px;
  margin: 0 0 18px;
}

.task-selection-summary--toolbar {
  margin: 0;
}

.page--matrix .matrix-axis {
  height: 100%;
}

.page-header {
  align-items: center;
  display: flex;
  gap: 16px;
  justify-content: space-between;
  margin-bottom: 18px;
}

.page-title {
  color: #e6e9ee;
  font-size: 24px;
  margin: 0;
}

.muted {
  color: #b1bac4;
  font-size: 13px;
}

@media (width < 40rem) {
  .topbar {
    padding: 12px 16px;
  }

  .nav {
    flex-basis: 100%;
    order: 3;
  }

  .nav a {
    flex: 1;
    justify-content: center;
  }

  .page {
    padding: 16px;
  }

  .page--matrix {
    height: auto;
    min-height: calc(100vh - 63px);
    padding: 16px;
  }

  .page--matrix .matrix-axis {
    height: auto;
  }

  .page--matrix > * {
    width: 100%;
  }

  .page-header {
    align-items: flex-start;
    flex-wrap: wrap;
  }
}

@media (width >= 40rem) {
  .topbar {
    flex-wrap: nowrap;
  }
}
`;
