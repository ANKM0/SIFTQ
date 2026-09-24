import { deleteCookie, setCookie } from "hono/cookie";
import type { Hono } from "hono";
import {
  SESSION_COOKIE_NAME,
  SESSION_DURATION_MS,
  createSession,
  isPasswordValid,
} from "../auth";
import { LoginPage, safeNextPath } from "../components/LoginPage";

type AuthEnv = {
  Bindings: {
    AUTH_PASSWORD?: string;
    SESSION_SECRET?: string;
  };
};

export function registerAuthRoutes<T extends AuthEnv>(app: Hono<T>) {
  app.get("/login", (c) => {
    const next = c.req.query("next");
    if (next === undefined) {
      return c.html(<LoginPage error={c.req.query("error") === "1"} />);
    }
    return c.html(<LoginPage error={c.req.query("error") === "1"} next={next} />);
  });

  app.post("/login", async (c) => {
    const password = c.env.AUTH_PASSWORD;
    const secret = c.env.SESSION_SECRET;
    if (password === undefined || secret === undefined) {
      return c.text("Authentication is not configured", 503);
    }

    const body = await c.req.parseBody();
    const submittedPassword = typeof body["password"] === "string" ? body["password"] : "";
    const next = typeof body["next"] === "string" ? body["next"] : "/ideas";

    if (!(await isPasswordValid(submittedPassword, password))) {
      return c.html(<LoginPage error next={next} />, 401);
    }

    const expires = Date.now() + SESSION_DURATION_MS;
    const session = await createSession(secret, expires);
    setCookie(c, SESSION_COOKIE_NAME, session, {
      httpOnly: true,
      sameSite: "Lax",
      secure: true,
      path: "/",
      expires: new Date(expires),
    });
    return c.redirect(safeNextPath(next));
  });

  app.post("/logout", (c) => {
    deleteCookie(c, SESSION_COOKIE_NAME, { path: "/" });
    return c.redirect("/login");
  });
}
