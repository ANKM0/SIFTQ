export const TASK_LIST_CSS = `
.list {
  border: 1px solid #d0d7de;
  border-radius: 8px;
  overflow: hidden;
}

.task-list-empty {
  color: #57606a;
  margin: 0;
  padding: 24px;
  text-align: center;
}

.task-row {
  align-items: center;
  border-radius: 0;
  border-width: 0 0 1px;
  display: grid;
  gap: 10px;
  grid-template-columns: 28px minmax(0, 1fr);
  padding: 12px 14px;
}

.task-row.is-selected {
  background: #ddf4ff;
}

.task-row-selection {
  align-items: center;
  display: flex;
  justify-content: center;
  margin: 0;
}

.task-row-selection input,
.task-select-all input {
  accent-color: #0969da;
  height: 20px;
  margin: 0;
  width: 20px;
}

.task-row-link {
  align-items: center;
  display: grid;
  gap: 10px;
  grid-template-columns: 48px minmax(0, 1fr);
  min-width: 0;
}

.task-row-link:focus-visible,
.task-row-selection:has(input:focus-visible) {
  outline: 2px solid #0969da;
  outline-offset: 2px;
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

.task-row:last-child {
  border-bottom: 0;
}

.task-list-shell {
  min-width: 0;
}

.task-list-toolbar {
  align-items: center;
  background: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  display: flex;
  gap: 12px;
  margin-bottom: 10px;
  min-height: 48px;
  padding: 8px 12px;
}

.task-select-all {
  align-items: center;
  display: flex;
  gap: 8px;
  margin: 0;
  white-space: nowrap;
}

.task-select-all input {
  flex: 0 0 auto;
}

.task-selection-count {
  white-space: nowrap;
}

.task-bulk-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-left: auto;
}

.task-bulk-actions [data-task-bulk-actions] {
  display: flex;
}

.task-bulk-actions [data-task-bulk-actions] {
  align-items: center;
  gap: 6px;
}

.task-bulk-actions button:disabled {
  color: #8c959f;
  cursor: default;
  opacity: 0.7;
}

.task-label-filter {
  position: relative;
}

.task-label-filter summary {
  cursor: pointer;
  list-style: none;
}

.task-label-filter summary::-webkit-details-marker {
  display: none;
}

.task-label-filter summary::after {
  content: "▾";
  margin-left: 6px;
}

.task-label-filter.is-active summary {
  background: #ddf4ff;
  border-color: #54aeff;
  color: #0969da;
}

.task-label-menu {
  background: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  box-shadow: 0 8px 24px rgb(31 35 40 / 18%);
  display: grid;
  gap: 2px;
  min-width: 140px;
  padding: 4px;
  position: absolute;
  right: 0;
  top: calc(100% + 4px);
  z-index: 3;
}

.task-label-menu a {
  border-radius: 4px;
  padding: 7px 8px;
}

.task-label-menu a:hover,
.task-label-menu a.is-selected {
  background: #eaeef2;
}

.task-bulk-menu {
  position: relative;
}

.task-bulk-menu summary {
  cursor: pointer;
  list-style: none;
}

.task-bulk-menu summary::-webkit-details-marker {
  display: none;
}

.task-bulk-menu summary::after {
  content: "▾";
  margin-left: 6px;
}

.task-bulk-menu-items {
  background: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  box-shadow: 0 8px 24px rgb(31 35 40 / 18%);
  display: grid;
  gap: 2px;
  min-width: 120px;
  padding: 4px;
  position: absolute;
  right: 0;
  top: calc(100% + 4px);
  z-index: 3;
}

.task-bulk-menu-items button {
  background: none;
  border: 0;
  border-radius: 4px;
  cursor: pointer;
  padding: 7px 8px;
  text-align: left;
}

.task-bulk-menu-items button:hover {
  background: #eaeef2;
}

.task-bulk-actions[hidden],
.task-selection-feedback[hidden] {
  display: none;
}

.task-selection-feedback {
  background: #dafbe1;
  border: 1px solid #4ac26b;
  border-radius: 6px;
  color: #1a7f37;
  margin: 0 0 10px;
  padding: 8px 12px;
}

.task-search {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.task-search input {
  flex: 1;
  min-width: 0;
}

.task-search-button {
  align-items: center;
  justify-content: center;
  min-width: 36px;
  padding: 7px;
}

.task-search-button svg {
  fill: none;
  height: 16px;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
  width: 16px;
}

.button--danger {
  color: #b00;
}

.pagination {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 18px;
}

.pagination .button.small.is-active {
  background: #2da44e;
  border-color: #2a9147;
  color: #ffffff;
}

.pagination .button.small.is-disabled {
  color: #8c959f;
  cursor: default;
}

.pagination-ellipsis {
  color: #57606a;
  font-weight: 700;
  padding: 0 4px;
}

`;

export const TASK_LIST_RESPONSIVE_CSS = `
@media (width < 40rem) {
  .task-list-toolbar {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .task-status-filter--toolbar {
    flex: 1;
    margin-bottom: 0;
  }

  .task-bulk-actions {
    margin-left: 0;
    width: 100%;
  }

  .task-bulk-actions .button {
    flex: 1;
  }

  .task-bulk-actions [data-task-bulk-actions] {
    flex: 1;
  }

  .task-bulk-menu {
    flex: 1;
  }

  .task-bulk-menu summary {
    justify-content: center;
    width: 100%;
  }
}
`;
