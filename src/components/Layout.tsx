import type { FC } from "hono/jsx";
import type { JSX } from "hono/jsx/jsx-runtime";
import { BRAND_NAME } from "../brand";

const HTMX_SCRIPT = "https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js";

export const Layout: FC<{ active: "ideas" | "matrix" | "tasks"; children?: JSX.Element }> = ({
  active,
  children,
}) => (
  <html lang="ja">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>{BRAND_NAME}</title>
      <link rel="stylesheet" href="/styles.css" />
      <script src={HTMX_SCRIPT} defer></script>
      <script src="/htmx-conflict.js" defer></script>
      <script src="/popover-dismiss.js" defer></script>
      <script src="/task-form-shortcut.js" defer></script>
      <script src="/description-editor.js" defer></script>
        <script src="/matrix-dnd.js" defer></script>
        <script src="/ideas-dnd.js" defer></script>
        <script src="/idea-detail.js" defer></script>
      <script src="/task-list-selection.js" defer></script>
    </head>
    <body>
      <header class="topbar">
        <a class="brand" href="/ideas">{BRAND_NAME}</a>
        <nav class="nav" aria-label="Primary">
          <a class={active === "ideas" ? "active" : undefined} href="/ideas">
            Ideas
          </a>
          <a class={active === "tasks" ? "active" : undefined} href="/tasks">
            Tasks
          </a>
          <a class={active === "matrix" ? "active" : undefined} href="/matrix">
            Matrix
          </a>
        </nav>
        <form action="/logout" method="post" class="logout">
          <button type="submit" class="button">Logout</button>
        </form>
      </header>
      <main id="page">{children}</main>
    </body>
  </html>
);
