import {
  HttpError,
  assertSameOrigin,
  checkLoginThrottle,
  clearLoginFailures,
  handle,
  recordLoginFailure,
  verifyPassword,
} from "@/lib/server/auth";
import { getUserWithHash } from "@/lib/server/repo";
import { withSession } from "@/lib/server/session-cookie";
import { LoginSchema, parseJson } from "@/lib/server/validation";

export const POST = handle(async (req: Request) => {
  assertSameOrigin(req);
  const { username, password } = await parseJson(req, LoginSchema);
  const key = username.toLowerCase();
  checkLoginThrottle(key);
  const found = getUserWithHash(username);
  if (!found || !verifyPassword(password, found.passwordHash)) {
    recordLoginFailure(key);
    throw new HttpError(401, "Wrong username or password");
  }
  clearLoginFailures(key);
  const { passwordHash: _omit, ...user } = found;
  void _omit;
  return withSession(req, user.id, { user });
});
