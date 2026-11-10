import fs from "node:fs/promises";
import path from "node:path";
import { HttpError, handle, requireUser } from "@/lib/server/auth";
import { UPLOAD_DIR } from "@/lib/server/db";
import { getFile } from "@/lib/server/repo";

// Only raster images render inline; everything else (incl. SVG/HTML) downloads.
const INLINE = new Set(["image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf"]);

export const GET = handle(async (req: Request, ctx: RouteContext<"/api/files/[id]">) => {
  await requireUser(req);
  const { id } = await ctx.params;
  const meta = /^file_[\w-]+$/.test(id) ? getFile(id) : null;
  if (!meta) throw new HttpError(404, "File not found");
  const data = await fs.readFile(path.join(UPLOAD_DIR, meta.id)).catch(() => null);
  if (!data) throw new HttpError(404, "File not found");
  const inline = INLINE.has(meta.mime);
  return new Response(new Uint8Array(data), {
    headers: {
      "Content-Type": inline ? meta.mime : "application/octet-stream",
      "Content-Disposition": `${inline ? "inline" : "attachment"}; filename*=UTF-8''${encodeURIComponent(meta.name)}`,
      "X-Content-Type-Options": "nosniff",
      "Cache-Control": "private, max-age=86400",
    },
  });
});
