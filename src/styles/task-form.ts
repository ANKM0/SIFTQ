export const TASK_FORM_CSS = `
.detail-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: minmax(0, 1fr);
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

.meta-row-link::marker {
  content: "";
}

.meta-row-link::-webkit-details-marker {
  display: none;
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
select,
.description-editor {
  background: #f1f3f6;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  font: inherit;
  padding: 9px 10px;
  width: 100%;
}

textarea {
  min-height: 180px;
}

.description-editor {
  background: #e6e9ee;
  min-height: 180px;
  overflow: auto;
  white-space: pre-wrap;
}

.description-editor a {
  color: inherit;
  text-decoration: underline;
}

textarea[data-description-value] {
  display: none;
}

.page--new,
.page--detail {
  display: flex;
  flex-direction: column;
  height: auto;
  min-height: calc(100vh - 63px);
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

.page--new .form-panel > label:has([data-description-editor]),
.page--detail .form-panel > label:has([data-description-editor]) {
  flex: 1;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 180px;
}

.page--new textarea,
.page--detail textarea,
.page--new .description-editor,
.page--detail .description-editor {
  height: 100%;
  min-height: 180px;
}

.form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.form-actions .button {
  flex: 1 1 140px;
  justify-content: center;
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
  background: #e6e9ee;
  border: 1px solid #d0d7de;
  border-radius: 12px;
  box-shadow: 0 16px 36px rgb(31 35 40 / 18%);
  display: grid;
  gap: 0;
  margin-top: 10px;
  min-width: 0;
  width: min(360px, calc(100vw - 32px));
  padding: 0;
  position: absolute;
  right: 0;
  top: 78px;
  z-index: 2;
}

details:not([open]) .popover {
  display: none;
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
  box-shadow: inset 4px 0 0 #1f883d;
}

button.status-choice {
  background: none;
  border: 0;
  color: inherit;
  cursor: pointer;
  font: inherit;
  text-align: left;
  width: 100%;
}

.check {
  align-items: center;
  background: #1f883d;
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
  background: #d0d7de;
}

.status-dot--one {
  background: #d0d7de;
}

.status-dot--two {
  background: #d0d7de;
}

.status-dot--three {
  background: #8b949e;
}

.status-dot--four {
  background: #57606a;
}

.status-dot--done {
  background: #86efac;
}

.status-dot--skip {
  background: #d1d5db;
}

@media (width >= 48rem) {
  .detail-grid {
    grid-template-columns: minmax(0, 1fr) 250px;
  }

  .page--new,
  .page--detail {
    height: calc(100vh - 63px);
    min-height: 480px;
  }

  .form-actions .button {
    flex: 0 0 auto;
  }
}
`;
