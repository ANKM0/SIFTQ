import { describe, expect, it } from "vite-plus/test";
import { createMemoryImageRepository } from "../src/repository/image-repository";
import type { StoredImage } from "../src/image";

function imageFixture(overrides: Partial<StoredImage> = {}): StoredImage {
  return {
    id: "image-1",
    owner_id: "local",
    content_type: "image/png",
    data: new Uint8Array([1, 2, 3]).buffer,
    created_at: "2026-01-01T00:00:00.000Z",
    ...overrides,
  };
}

describe("MemoryImageRepository", () => {
  it("stores and finds an image for its owner", async () => {
    const repository = createMemoryImageRepository();
    const image = imageFixture();

    expect(await repository.insert(image)).toEqual({ ok: true, value: image });
    expect(await repository.find("image-1", "local")).toEqual({ ok: true, value: image });
  });

  it("does not return another owner's image", async () => {
    const repository = createMemoryImageRepository();
    await repository.insert(imageFixture());

    expect(await repository.find("image-1", "other")).toEqual({ ok: true, value: undefined });
  });

  it("returns undefined for an unknown image", async () => {
    const repository = createMemoryImageRepository();

    expect(await repository.find("missing", "local")).toEqual({ ok: true, value: undefined });
  });
});
