import { db } from "@/lib/server/db";

export function GET() {
  db.prepare("SELECT 1").get();
  return Response.json({ ok: true });
}
