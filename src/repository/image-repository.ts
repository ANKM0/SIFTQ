import type { D1Database } from "@cloudflare/workers-types";
import { isRecord, ok } from "../task";
import type { Result } from "../task";
import { isImageContentType } from "../image";
import type { StoredImage } from "../image";

export type ImageRepositoryError = { code: "NOT_FOUND" | "CONFLICT" };

export interface ImageRepository {
  insert(image: StoredImage): Promise<Result<StoredImage, ImageRepositoryError>>;
  find(id: string, owner_id: string): Promise<Result<StoredImage | undefined, ImageRepositoryError>>;
}

export function createMemoryImageRepository(): ImageRepository {
  const images = new Map<string, StoredImage>();

  return {
    async insert(image) {
      images.set(image.id, image);
      return ok(image);
    },
    async find(id, owner_id) {
      const image = images.get(id);
      return ok(image?.owner_id === owner_id ? image : undefined);
    },
  };
}

function toStoredImage(value: unknown): StoredImage | undefined {
  if (!isRecord(value)) return undefined;
  const { id, owner_id, content_type, data, created_at } = value;
  if (typeof id !== "string") return undefined;
  if (typeof owner_id !== "string") return undefined;
  if (typeof content_type !== "string") return undefined;
  if (!isImageContentType(content_type)) return undefined;
  if (!(data instanceof ArrayBuffer)) return undefined;
  if (typeof created_at !== "string") return undefined;
  return { id, owner_id, content_type, data, created_at };
}

export function createD1ImageRepository(db: D1Database): ImageRepository {
  return {
    async insert(image) {
      await db
        .prepare("INSERT INTO images (id, owner_id, content_type, data, created_at) VALUES (?, ?, ?, ?, ?)")
        .bind(image.id, image.owner_id, image.content_type, image.data, image.created_at)
        .run();
      return ok(image);
    },
    async find(id, owner_id) {
      const row = await db
        .prepare("SELECT id, owner_id, content_type, data, created_at FROM images WHERE id = ? AND owner_id = ?")
        .bind(id, owner_id)
        .first<Record<string, unknown>>();
      return ok(row === null ? undefined : toStoredImage(row));
    },
  };
}
