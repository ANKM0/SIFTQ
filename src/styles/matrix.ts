export const MATRIX_CSS = `
.matrix {
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(0, 1fr);
}

.page--matrix .error {
  color: #e6e9ee;
}

.matrix-axis {
  background: #aeb8c4;
  border: 1px solid #8b949e;
  border-radius: 8px;
  gap: 12px;
  grid-template-rows: repeat(4, minmax(0, auto));
  min-height: auto;
  padding: 20px;
  position: relative;
}

.axis-line {
  color: #3f4854;
  display: none;
  font-size: 13px;
  font-weight: 700;
  pointer-events: none;
  position: absolute;
  z-index: 0;
}

.axis-line::before {
  background: #3f4854;
  content: "";
  position: absolute;
}

.axis-line::after {
  border-color: #3f4854;
  border-style: solid;
  content: "";
  position: absolute;
}

.axis-line span {
  background: #c1c9d3;
  border: 1px solid #8b949e;
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
  background: #c1c9d3;
  border: 1px solid #8b949e;
  border-radius: 8px;
  min-height: 280px;
  padding: 14px;
}

.area--quadrant {
  background: transparent;
  border: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  position: relative;
  z-index: 1;
}

.area--quadrant .matrix-cards {
  flex: 1;
  min-height: 0;
  overflow-y: visible;
}

.area-create-link {
  inset: 0;
  position: absolute;
  z-index: 0;
}

.matrix-create-link {
  display: none;
  position: absolute;
  z-index: 0;
}

.matrix-create-link--q1 {
  inset: 0 50% 50% 0;
}

.matrix-create-link--q2 {
  inset: 0 0 50% 50%;
}

.matrix-create-link--q3 {
  inset: 50% 50% 0 0;
}

.matrix-create-link--q4 {
  inset: 50% 0 0 50%;
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
  grid-column: 1;
  grid-row: 2;
}

.area--q3 {
  grid-column: 1;
  grid-row: 3;
}

.area--q4 {
  grid-column: 1;
  grid-row: 4;
}

.area h2 {
  align-items: center;
  display: flex;
  font-size: 16px;
  justify-content: space-between;
  margin: 0 0 12px;
}

.task-card,
.task-row {
  background: #c1c9d3;
  border: 1px solid #8b949e;
  border-radius: 8px;
}

.form-panel,
.side-panel,
.state-card {
  background: #c1c9d3;
  border: 1px solid #8b949e;
  border-radius: 8px;
}

.task-card {
  border-color: #1b1f24;
  box-shadow: 0 1px 2px rgb(31 35 40 / 12%);
  display: flex;
  flex-direction: column;
  margin-bottom: 12px;
  min-height: 72px;
  padding: 12px;
  -webkit-user-select: none;
  user-select: none;
}

.task-card--working,
.task-row--working {
  border-left: 4px solid #0f4d24;
}

.task-card:hover {
  border-color: #1f883d;
  box-shadow: 0 0 0 2px #b7e3c3;
}

.task-card-header {
  align-items: flex-start;
  display: flex;
  gap: 8px;
  justify-content: space-between;
}

.task-card.dragging {
  border-color: #1f883d;
  box-shadow: 0 0 0 3px #b7e3c3;
  opacity: 0.72;
}

.matrix-drag-ghost {
  left: 0;
  margin: 0;
  opacity: 0.85;
  pointer-events: none;
  position: fixed;
  top: 0;
  z-index: 100;
}

.matrix-drag-placeholder {
  background: #b7e3c3;
  flex: none;
  margin-bottom: 12px;
  pointer-events: none;
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

.area-badge {
  background: transparent;
  border-color: #8b949e;
  color: #3f4854;
}

.status--do {
  background: transparent;
  border-color: #1b1f24;
  color: #1b1f24;
}

.status--done {
  background: #b7e3c3;
  border-color: #4ac26b;
  color: #0f4d24;
}

.status--skip {
  background: #f6f8fa;
  border-color: #8b949e;
  color: #3f4854;
}

.working-badge {
  align-items: center;
  background: transparent;
  border: 1px solid #0f4d24;
  border-radius: 999px;
  color: #0f4d24;
  display: inline-flex;
  font-size: 12px;
  font-weight: 700;
  gap: 5px;
  padding: 3px 8px;
  width: max-content;
}

.working-badge::before {
  background: #0f4d24;
  border-radius: 50%;
  content: "";
  height: 6px;
  width: 6px;
}

`;

export const MATRIX_ACTIONS_CSS = `

.state-map {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.drop-line {
  border: 2px dashed #0f4d24;
  border-radius: 6px;
  color: #0f4d24;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 10px;
  padding: 10px;
  text-align: center;
}

.matrix-menu {
  background: #c1c9d3;
  border: 1px solid #8b949e;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgb(31 35 40 / 18%);
  display: grid;
  min-width: 220px;
  padding: 6px;
  position: fixed;
  z-index: 50;
}

.matrix-menu-item {
  background: none;
  border: 0;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  padding: 8px 10px;
  text-align: left;
}

.matrix-menu-item:hover {
  background: #eaeef2;
}

.matrix-menu-item--delete {
  color: #1b1f24;
}

.matrix-modal-backdrop {
  align-items: center;
  background: rgb(31 35 40 / 45%);
  display: flex;
  inset: 0;
  justify-content: center;
  padding: 24px;
  position: fixed;
  z-index: 100;
}

.matrix-modal {
  background: #c1c9d3;
  border: 1px solid #8b949e;
  border-radius: 12px;
  box-shadow: 0 16px 36px rgb(31 35 40 / 30%);
  display: flex;
  flex-direction: column;
  height: 160px;
  justify-content: space-between;
  max-width: 90vw;
  padding: 16px 20px;
  width: 320px;
}

.matrix-modal-text {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
}

.matrix-modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.matrix-modal-button {
  border: 1px solid #8b949e;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  min-height: 34px;
  padding: 7px 16px;
}

.matrix-modal-button--cancel {
  background: #c1c9d3;
}

.matrix-modal-button--cancel:hover {
  background: #eaeef2;
}

.matrix-modal-button--danger {
  background: #1b1f24;
  border-color: #1b1f24;
  color: #ffffff;
}

.matrix-modal-button--danger:hover {
  background: #1b1f24;
}

@media (width >= 40rem) {
  .matrix {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .matrix-axis {
    gap: 54px;
    grid-template-rows: repeat(2, minmax(0, 1fr));
    min-height: 0;
    padding: 72px 20px;
  }

  .axis-line,
  .matrix-create-link {
    display: block;
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

  .area--quadrant .matrix-cards {
    overflow-y: auto;
  }
}
`;
