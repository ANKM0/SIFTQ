export const STYLES_CSS = `
.page { padding: 1rem; }
.matrix { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
.matrix-area { border: 1px solid #ccc; padding: 0.5rem; }
.matrix-cards { min-height: 6rem; }
.task-card { display: block; padding: 0.5rem; border: 1px solid #ddd; margin: 0.25rem 0; }
.task-title { overflow-wrap: anywhere; }
.task-list { list-style: none; padding: 0; }
.task-row { display: flex; gap: 1rem; padding: 0.5rem; border-bottom: 1px solid #eee; }
.status-badge, .area-badge { padding: 0.125rem 0.5rem; border-radius: 999px; background: #eee; }
.error { color: #b00; }
.page--empty { min-height: 10rem; }
.page--loading { opacity: 0.6; }
.page--error { border-left: 4px solid #b00; }
`;
