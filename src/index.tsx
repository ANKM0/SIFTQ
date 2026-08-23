import { Hono } from "hono";

const app = new Hono();

app.get("/", (c) =>
  c.html(
    <html lang="ja">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>SIFTQ</title>
      </head>
      <body>
        <main>
          <h1>SIFTQ</h1>
        </main>
      </body>
    </html>
  )
);

export default app;
