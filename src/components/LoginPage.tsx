import type { JSX } from "hono/jsx/jsx-runtime";

export function safeNextPath(next: string | undefined): string {
  if (next !== undefined && next.startsWith("/") && !next.startsWith("//")) return next;
  return "/";
}

export function LoginPage({
  error = false,
  next,
}: {
  error?: boolean;
  next?: string;
}): JSX.Element {
  return (
    <html lang="ja">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>SIFTQ</title>
        <link rel="stylesheet" href="/styles.css" />
      </head>
      <body>
        <main class="login">
          <form class="login-card" method="post" action="/login">
            <h1 class="brand">SIFTQ</h1>
            <input type="hidden" name="next" value={safeNextPath(next)} />
            <label>
              Password
              <input type="password" name="password" required />
            </label>
            {error ? <p class="error">Incorrect password</p> : null}
            <button class="button primary" type="submit">
              Sign in
            </button>
          </form>
        </main>
      </body>
    </html>
  );
}
