import fs from "node:fs/promises";
import path from "node:path";
import { HttpError, handle, requireUser } from "@/lib/server/auth";
import { UPLOAD_DIR } from "@/lib/server/db";
import { insertFile } from "@/lib/server/repo";
import { uid } from "@/lib/ids";

const MAX_BYTES = 15 * 1024 * 1024;

export const POST = handle(async (req: Request) => {
  const me = await requireUser(req);
  const form = await req.formData().catch(() => null);
  const file = form?.get("file");
  if (!(file instanceof File)) throw new HttpError(400, "Expected a 'file' field");
  if (file.size > MAX_BYTES) throw new HttpError(413, "Files are limited to 15 MB");

  const id = uid("file");
  await fs.mkdir(UPLOAD_DIR, { recursive: true });
  await fs.writeFile(path.join(UPLOAD_DIR, id), Buffer.from(await file.arrayBuffer()));
  const name = file.name.replace(/[\r\n"\\/]/g, "_").slice(0, 200) || "file";
  const mime = file.type || "application/octet-stream";
  insertFile({ id, name, mime, size: file.size, uploadedBy: me.id });
  return Response.json({ file: { id, name, mime, size: file.size, url: `/api/files/${id}` } }, { status: 201 });
});
