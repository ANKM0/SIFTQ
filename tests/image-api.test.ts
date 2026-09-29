import { beforeEach, describe, expect, it } from "vite-plus/test";
import app from "../src/index";
import { createSession, SESSION_COOKIE_NAME } from "../src/auth";
import { createMemoryImageRepository } from "../src/repository/image-repository";
import type { ImageRepository } from "../src/repository/image-repository";
import { IMAGE_MAX_BYTES } from "../src/image";

const SECRET = "image-api-test-secret";
const PASSWORD = atob("dGVzdC1wYXNzd29yZA==");

let repository: ImageRepository;

beforeEach(() => {
  repository = createMemoryImageRepository();
});

function bindings() {
  return { AUTH_PASSWORD: PASSWORD, SESSION_SECRET: SECRET, IMAGE_REPOSITORY: repository };
}

async function request(path: string, init: RequestInit = {}) {
  const cookie = await createSession(SECRET, Date.now() + 60_000);
  const headers = new Headers(init.headers);
  headers.set("Cookie", `${SESSION_COOKIE_NAME}=${cookie}`);
  return app.request(path, { ...init, headers }, bindings());
}

function bytes(...values: number[]): ArrayBuffer {
  const buffer = new ArrayBuffer(values.length);
  new Uint8Array(buffer).set(values);
  return buffer;
}

function uploadForm(data: ArrayBuffer, name: string, type: string): FormData {
  const form = new FormData();
  form.append("file", new File([data], name, { type }));
  return form;
}

describe("Image API upload", () => {
  it("stores an uploaded image and serves it back", async () => {
    const payload = bytes(137, 80, 78, 71, 13, 10, 26, 10);
    const created = await request("/api/images", { method: "POST", body: uploadForm(payload, "pixel.png", "image/png") });
    expect(created.status).toBe(201);

    const body: { id: string; url: string } = await created.json();
    expect(body.url).toBe(`/api/images/${body.id}`);

    const fetched = await request(body.url);
    expect(fetched.status).toBe(200);
    expect(fetched.headers.get("content-type")).toContain("image/png");
    expect(new Uint8Array(await fetched.arrayBuffer())).toEqual(new Uint8Array(payload));
  });

  it("accepts webp and jpeg uploads", async () => {
    const webp = await request("/api/images", { method: "POST", body: uploadForm(bytes(1), "a.webp", "image/webp") });
    const jpeg = await request("/api/images", { method: "POST", body: uploadForm(bytes(2), "a.jpg", "image/jpeg") });

    expect(webp.status).toBe(201);
    expect(jpeg.status).toBe(201);
  });

  it("rejects an unsupported image type", async () => {
    const response = await request("/api/images", { method: "POST", body: uploadForm(bytes(1, 2, 3), "a.gif", "image/gif") });
    const body: { code?: string } = await response.json();

    expect(response.status).toBe(400);
    expect(body.code).toBe("UNSUPPORTED_IMAGE");
  });

  it("rejects an image larger than one mebibyte", async () => {
    const response = await request("/api/images", {
      method: "POST",
      body: uploadForm(new ArrayBuffer(IMAGE_MAX_BYTES + 1), "huge.png", "image/png"),
    });
    const body: { code?: string } = await response.json();

    expect(response.status).toBe(400);
    expect(body.code).toBe("IMAGE_TOO_LARGE");
  });

  it("rejects a request without a file", async () => {
    const response = await request("/api/images", { method: "POST", body: new FormData() });
    const body: { code?: string } = await response.json();

    expect(response.status).toBe(400);
    expect(body.code).toBe("INVALID_IMAGE");
  });
});

describe("Image API access", () => {
  it("returns not found for an unknown image", async () => {
    const response = await request("/api/images/does-not-exist");
    const body: { code?: string } = await response.json();

    expect(response.status).toBe(404);
    expect(body.code).toBe("NOT_FOUND");
  });

  it("requires authentication", async () => {
    const response = await app.request("/api/images", { method: "POST", body: new FormData() }, bindings());

    expect(response.status).toBe(401);
  });
});
