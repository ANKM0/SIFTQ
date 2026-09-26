export const BASE_CSS = `
:root {
  color: #1b1f24;
  background: #30363d;
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
  outline: 2px solid #1f883d;
  outline-offset: 2px;
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
  background: #ffffff;
  border-bottom: 1px solid #d0d7de;
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
  background: #e6e9ee;
  border: 1px solid #d0d7de;
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
  color: #e6e9ee;
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
