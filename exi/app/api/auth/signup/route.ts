import crypto from "node:crypto";
import { HttpError, assertSameOrigin, handle, hashPassword } from "@/lib/server/auth";
import { countUsers, createUser, ensureDefaultChannels, getUserWithHash } from "@/lib/server/repo";
import { withSession } from "@/lib/server/session-cookie";
import { SignupSchema, parseJson } from "@/lib/server/validation";

/**
 * Sign-up policy: the very first account can always be created (workspace owner).
 * After that, EXI_INVITE_CODE must be set and supplied — otherwise sign-up is closed.
 */
export const POST = handle(async (req: Request) => {
  assertSameOrigin(req);
  const body = await parseJson(req, SignupSchema);
  const invite = process.env.EXI_INVITE_CODE;
  if (countUsers() > 0) {
    if (!invite) throw new HttpError(403, "Sign-up is closed. Ask the admin to set EXI_INVITE_CODE.");
    const a = Buffer.from(body.inviteCode ?? "");
    const b = Buffer.from(invite);
    if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) throw new HttpError(403, "Invalid invite code");
  }
  if (getUserWithHash(body.username)) throw new HttpError(409, "That username is taken");
  const user = createUser(body.username, body.displayName, hashPassword(body.password));
  ensureDefaultChannels();
  return withSession(req, user.id, { user }, 201);
});
