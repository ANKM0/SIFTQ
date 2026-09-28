import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize, resolve } from "node:path";

const CONTENT_TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".svg": "image/svg+xml",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".css": "text/css; charset=utf-8",
};

export type Served = { url: string; close: () => void };

export function serveDir(dir: string, port: number): Promise<Served> {
  const root = resolve(dir);
  const server = createServer((req, res) => {
    void (async () => {
      try {
        const url = new URL(req.url ?? "/", "http://localhost");
        const pathname = decodeURIComponent(url.pathname);
        const relative = pathname === "/" ? "/viewer.html" : pathname;
        const filePath = normalize(join(root, relative));
        if (filePath !== root && !filePath.startsWith(root + "/")) {
          res.writeHead(403);
          res.end("Forbidden");
          return;
        }
        const data = await readFile(filePath);
        res.writeHead(200, { "content-type": CONTENT_TYPES[extname(filePath)] ?? "application/octet-stream" });
        res.end(data);
      } catch {
        res.writeHead(404);
        res.end("Not found");
      }
    })();
  });
  return new Promise((resolvePromise) => {
    server.listen(port, () => resolvePromise({ url: `http://localhost:${port}/viewer.html`, close: () => server.close() }));
  });
}
