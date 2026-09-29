export const IMAGE_CONTENT_TYPES = ["image/png", "image/webp", "image/jpeg"] as const;

export type ImageContentType = (typeof IMAGE_CONTENT_TYPES)[number];

export const IMAGE_MAX_BYTES = 1024 * 1024;

export type StoredImage = {
  id: string;
  owner_id: string;
  content_type: ImageContentType;
  data: ArrayBuffer;
  created_at: string;
};

export function isImageContentType(value: string): value is ImageContentType {
  return IMAGE_CONTENT_TYPES.some((contentType) => contentType === value);
}
