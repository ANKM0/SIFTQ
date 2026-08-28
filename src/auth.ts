const encoder = new TextEncoder();

export const SESSION_COOKIE_NAME = "siftq_session";
export const SESSION_DURATION_MS = 7 * 24 * 60 * 60 * 1000;

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let difference = 0;
  for (let index = 0; index < a.length; index += 1) {
    difference |= a.charCodeAt(index) ^ b.charCodeAt(index);
  }
  return difference === 0;
}

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(value));
  return bytesToHex(new Uint8Array(digest));
}

async function sign(secret: string, payload: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(payload));
  return btoa(String.fromCharCode(...Array.from(new Uint8Array(signature))));
}

export async function createSession(secret: string, expires: number): Promise<string> {
  const payload = `v1.${expires}`;
  return `${payload}.${await sign(secret, payload)}`;
}

export async function isValidSession(secret: string, value: string): Promise<boolean> {
  const separator = value.lastIndexOf(".");
  if (separator < 0) return false;

  const payload = value.slice(0, separator);
  const suppliedSignature = value.slice(separator + 1);
  if (!/^v1\.\d+$/.test(payload)) return false;

  const expires = Number(payload.slice(3));
  if (!Number.isInteger(expires) || expires < Date.now()) return false;

  const expectedSignature = await sign(secret, payload);
  return timingSafeEqual(expectedSignature, suppliedSignature);
}

export async function isPasswordValid(input: string, expected: string): Promise<boolean> {
  const [inputDigest, expectedDigest] = await Promise.all([sha256(input), sha256(expected)]);
  return timingSafeEqual(inputDigest, expectedDigest);
}
