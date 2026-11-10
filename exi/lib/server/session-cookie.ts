import { SESSION_COOKIE, createSession, isSecureRequest } from "./auth";

/** JSON response that also sets a fresh session cookie for `userId`. */
export function withSession(req: Request, userId: string, body: unknown, status = 200): Response {
  const { token, expiresAt } = createSession(userId);
  const res = Response.json(body, { status });
  const parts = [
    `${SESSION_COOKIE}=${token}`,
    "Path=/",
    "HttpOnly",
    "SameSite=Lax",
    `Expires=${new Date(expiresAt).toUTCString()}`,
  ];
  if (isSecureRequest(req)) parts.push("Secure");
  res.headers.append("Set-Cookie", parts.join("; "));
  return res;
}

export function clearSession(req: Request, body: unknown): Response {
  const res = Response.json(body);
  const parts = [`${SESSION_COOKIE}=`, "Path=/", "HttpOnly", "SameSite=Lax", "Max-Age=0"];
  if (isSecureRequest(req)) parts.push("Secure");
  res.headers.append("Set-Cookie", parts.join("; "));
  return res;
}
