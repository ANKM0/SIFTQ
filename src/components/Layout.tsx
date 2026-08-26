import type { FC } from "hono/jsx";

const HTMX_SCRIPT = "https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js";

export const Layout: FC = ({ children }) => (
  <html lang="ja">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>SIFTQ</title>
      <script src={HTMX_SCRIPT} defer></script>
    </head>
    <body>
      <main id="page">{children}</main>
    </body>
  </html>
);
