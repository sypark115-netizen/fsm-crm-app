import { cookies } from "next/headers";
import { SESSION_COOKIE, assertSameOrigin, deleteSession, handle } from "@/lib/server/auth";
import { clearSession } from "@/lib/server/session-cookie";

export const POST = handle(async (req: Request) => {
  assertSameOrigin(req);
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (token) deleteSession(token);
  return clearSession(req, { ok: true });
});
