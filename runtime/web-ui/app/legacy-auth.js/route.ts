import { readFile } from "node:fs/promises";
import { join } from "node:path";
export const runtime = "nodejs";
export async function GET() {
  const script = await readFile(join(process.cwd(), "assets", "google-auth.js"), "utf8");
  return new Response(script, {
    headers: { "content-type": "text/javascript; charset=utf-8", "cache-control": "no-store", "x-content-type-options": "nosniff" },
  });
}
