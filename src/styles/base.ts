export const BASE_CSS = `
:root {
  color: #24292f;
  background: #f6f8fa;
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
  background: #ffffff;
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
  background: #2da44e;
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
  background: #2da44e;
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
  color: #24292f;
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
  font-size: 24px;
  margin: 0;
}

.muted {
  color: #57606a;
  font-size: 13px;
}
`;
