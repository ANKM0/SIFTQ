import type { Context, Hono } from "hono";
import { IMAGE_MAX_BYTES, isImageContentType } from "../image";
import type { StoredImage } from "../image";
import type { ImageRepository } from "../repository/image-repository";
import type { AppEnv } from "../app-env";

const OWNER_ID = "local";

export function registerImageApiRoutes(
  app: Hono<AppEnv>,
  repository: (c: Context<AppEnv>) => ImageRepository,
) {
  app.post("/api/images", async (c) => {
    let form: FormData;
    try {
      form = await c.req.formData();
    } catch {
      return c.json({ code: "INVALID_IMAGE" }, 400);
    }
    const file = form.get("file");
    if (file === null || typeof file === "string") return c.json({ code: "INVALID_IMAGE" }, 400);
    if (!isImageContentType(file.type)) return c.json({ code: "UNSUPPORTED_IMAGE" }, 400);
    const data = await file.arrayBuffer();
    if (data.byteLength === 0) return c.json({ code: "INVALID_IMAGE" }, 400);
    if (data.byteLength > IMAGE_MAX_BYTES) return c.json({ code: "IMAGE_TOO_LARGE" }, 400);

    const image: StoredImage = {
      id: crypto.randomUUID(),
      owner_id: OWNER_ID,
      content_type: file.type,
      data,
      created_at: new Date().toISOString(),
    };
    const inserted = await repository(c).insert(image);
    if (!inserted.ok) return c.json({ code: inserted.error.code }, 500);
    return c.json({ id: inserted.value.id, url: `/api/images/${inserted.value.id}` }, 201);
  });

  app.get("/api/images/:id", async (c) => {
    const found = await repository(c).find(c.req.param("id"), OWNER_ID);
    if (!found.ok) return c.json({ code: found.error.code }, 500);
    if (!found.value) return c.json({ code: "NOT_FOUND" }, 404);
    return c.body(found.value.data, 200, {
      "content-type": found.value.content_type,
      "cache-control": "public, max-age=31536000, immutable",
    });
  });
}
