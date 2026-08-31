export const STYLES_CSS = `
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

.matrix {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.matrix-axis {
  background: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  gap: 54px;
  min-height: 0;
  padding: 72px 20px;
  position: relative;
}

.axis-line {
  color: #57606a;
  font-size: 13px;
  font-weight: 700;
  position: absolute;
  z-index: 0;
}

.axis-line::before {
  background: #57606a;
  content: "";
  position: absolute;
}

.axis-line::after {
  border-color: #57606a;
  border-style: solid;
  content: "";
  position: absolute;
}

.axis-line span {
  background: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 999px;
  padding: 4px 10px;
  position: absolute;
  white-space: nowrap;
}

.axis-line--horizontal {
  inset: 50% 20px auto;
  transform: translateY(-50%);
}

.axis-line--horizontal::before {
  height: 2px;
  left: 0;
  right: 18px;
  top: 0;
}

.axis-line--horizontal::after {
  border-width: 2px 2px 0 0;
  height: 12px;
  right: 4px;
  top: -5px;
  transform: rotate(45deg);
  width: 12px;
}

.axis-line--horizontal span {
  right: 32px;
  top: -38px;
}

.axis-line--vertical {
  inset: 72px auto 72px 50%;
  transform: translateX(-50%);
}

.axis-line--vertical::before {
  bottom: 0;
  left: 0;
  top: 18px;
  width: 2px;
}

.axis-line--vertical::after {
  border-width: 2px 0 0 2px;
  height: 12px;
  left: -5px;
  top: 4px;
  transform: rotate(45deg);
  width: 12px;
}

.axis-line--vertical span {
  left: 12px;
  top: -44px;
}

.area {
  background: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  min-height: 280px;
  padding: 14px;
}

.area--quadrant {
  background: transparent;
  border: 0;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
}

.area--quadrant .matrix-cards {
  flex: 1;
  min-height: 0;
}

.area-create-link {
  inset: 0;
  position: absolute;
  z-index: 0;
}

.area--quadrant h2,
.area--quadrant .matrix-cards {
  position: relative;
  z-index: 1;
}

.area--q1 {
  grid-column: 1;
  grid-row: 1;
}

.area--q2 {
  grid-column: 2;
  grid-row: 1;
}

.area--q3 {
  grid-column: 1;
  grid-row: 2;
}

.area--q4 {
  grid-column: 2;
  grid-row: 2;
}

.area h2 {
  align-items: center;
  display: flex;
  font-size: 16px;
  justify-content: space-between;
  margin: 0 0 12px;
}

.task-card,
.task-row,
.form-panel,
.side-panel,
.state-card {
  background: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 8px;
}

.task-card {
  box-shadow: 0 1px 2px rgb(31 35 40 / 12%);
  display: flex;
  flex-direction: column;
  margin-bottom: 12px;
  min-height: 72px;
  padding: 12px;
}

.task-card:hover {
  border-color: #0969da;
  box-shadow: 0 0 0 2px #ddf4ff;
}

.task-card-header {
  align-items: flex-start;
  display: flex;
  gap: 8px;
  justify-content: space-between;
}

.task-card[draggable="true"] {
  cursor: grab;
}

.task-card[draggable="true"]:active {
  cursor: grabbing;
}

.task-card.dragging {
  border-color: #0969da;
  box-shadow: 0 0 0 3px #ddf4ff;
  opacity: 0.72;
}

.area--quadrant.drop-target {
  background: #f6f8fa;
  border-radius: 8px;
}

.task-title {
  font-weight: 700;
}

.status {
  border: 1px solid transparent;
  border-radius: 999px;
  display: inline-flex;
  font-size: 12px;
  font-weight: 700;
  padding: 3px 8px;
  width: max-content;
}

.area-badge,
.status--do {
  background: #ddf4ff;
  border-color: #54aeff;
  color: #0969da;
}

.status--done {
  background: #dafbe1;
  border-color: #4ac26b;
  color: #1a7f37;
}

.status--skip {
  background: #f6f8fa;
  border-color: #d0d7de;
  color: #57606a;
}

.list {
  border: 1px solid #d0d7de;
  border-radius: 8px;
  overflow: hidden;
}

.task-row {
  align-items: center;
  border-radius: 0;
  border-width: 0 0 1px;
  display: grid;
  gap: 10px;
  grid-template-columns: 48px minmax(0, 1fr);
  padding: 12px 14px;
}

.task-row-main {
  display: grid;
  gap: 4px;
}

.task-row-title {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  column-gap: 10px;
  row-gap: 6px;
}

.issue-number {
  color: #57606a;
  font-size: 13px;
  font-weight: 700;
}

.task-row:last-child {
  border-bottom: 0;
}

.detail-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: minmax(0, 1fr) 250px;
}

.form-panel,
.side-panel,
.state-card {
  padding: 16px;
}

.side-panel--popover-open {
  position: relative;
}

.meta-row {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.meta-row-link {
  border-radius: 6px;
  margin: -6px -6px 0;
  padding: 6px;
}

.meta-row-link:hover {
  background: #eaeef2;
  cursor: pointer;
}

.meta-row h2 {
  font-size: 16px;
  margin: 0;
}

.meta-row--spaced {
  border-top: 1px solid #d0d7de;
  margin-top: 16px;
  padding-top: 16px;
}

.meta-caret {
  align-items: center;
  border: 0;
  color: #57606a;
  display: inline-flex;
  font-size: 20px;
  justify-content: center;
  min-height: 32px;
  min-width: 32px;
}

label {
  display: grid;
  font-size: 13px;
  font-weight: 700;
  gap: 6px;
  margin-bottom: 14px;
}

input,
textarea,
select {
  border: 1px solid #d0d7de;
  border-radius: 6px;
  font: inherit;
  padding: 9px 10px;
  width: 100%;
}

textarea {
  min-height: 180px;
}

.page--new,
.page--detail {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 63px);
  min-height: 480px;
}

.page--new .detail-grid,
.page--detail .detail-grid {
  flex: 1;
  min-height: 0;
}

.page--new .form-panel,
.page--detail .form-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.page--new .form-panel > label:has(textarea),
.page--detail .form-panel > label:has(textarea) {
  flex: 1;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 180px;
}

.page--new textarea,
.page--detail textarea {
  height: 100%;
  min-height: 180px;
}

.form-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.status-menu {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.status-option {
  border: 1px solid #d0d7de;
  border-radius: 6px;
  padding: 10px;
}

.popover {
  background: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 12px;
  box-shadow: 0 16px 36px rgb(31 35 40 / 18%);
  display: grid;
  gap: 0;
  margin-top: 10px;
  min-width: 360px;
  padding: 0;
  position: absolute;
  right: 0;
  top: 78px;
  z-index: 2;
}

.popover h3 {
  font-size: 16px;
  margin: 0;
  padding: 16px 16px 8px;
}

.status-group-title {
  background: #f6f8fa;
  border-bottom: 1px solid #d0d7de;
  border-top: 1px solid #d0d7de;
  color: #57606a;
  font-size: 13px;
  font-weight: 700;
  padding: 10px 16px;
}

.status-choice {
  align-items: start;
  display: grid;
  gap: 10px;
  grid-template-columns: 20px 16px 1fr;
  padding: 12px 16px;
}

.status-choice.selected {
  background: #f6f8fa;
  box-shadow: inset 4px 0 0 #0969da;
}

.check {
  align-items: center;
  background: #0969da;
  border-radius: 4px;
  color: #ffffff;
  display: inline-flex;
  font-weight: 700;
  height: 20px;
  justify-content: center;
  width: 20px;
}

.box {
  border: 1px solid #8c959f;
  border-radius: 4px;
  display: inline-flex;
  height: 20px;
  width: 20px;
}

.status-dot {
  border-radius: 999px;
  display: inline-flex;
  height: 16px;
  margin-top: 2px;
  width: 16px;
}

.status-dot--do {
  background: #bfdbfe;
}

.status-dot--one {
  background: #bfdbfe;
}

.status-dot--two {
  background: #bfdbfe;
}

.status-dot--three {
  background: #fef08a;
}

.status-dot--four {
  background: #fde68a;
}

.status-dot--done {
  background: #86efac;
}

.status-dot--skip {
  background: #d1d5db;
}

.state-map {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.drop-line {
  border: 2px dashed #0969da;
  border-radius: 6px;
  color: #0969da;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 10px;
  padding: 10px;
  text-align: center;
}

.error { color: #b00; }
button { font: inherit; }

.login {
  align-items: center;
  display: flex;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
}

.login-card {
  background: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  display: grid;
  gap: 16px;
  max-width: 360px;
  padding: 24px;
  width: 100%;
}

.login-card label {
  display: grid;
  font-size: 14px;
  font-weight: 600;
  gap: 6px;
}

.login-card input {
  border: 1px solid #d0d7de;
  border-radius: 6px;
  font: inherit;
  min-height: 34px;
  padding: 6px 10px;
}
`;
